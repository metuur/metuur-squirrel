#!/usr/bin/env python3
"""
deadline_scanner.py — Escanea todos los intents del vault, agrupa por urgencia.

Es el "motor de parakeet": clasifica deadlines en 6 niveles canónicos y devuelve
JSON estructurado para que el skill parakeet componga los mensajes con tono.

Niveles canónicos (ATTN-001):
  - critical:   deadline hoy con < 4 h restantes, O deadline ya pasado (is_overdue=True)
  - urgent:     deadline hoy con ≥ 4 h, O mañana (1 día)
  - soon:       2–3 días
  - upcoming:   4–7 días
  - eventual:   8–30 días
  - distant:    > 30 días

Los items con deadline pasado quedan en `critical` con `is_overdue=True` y `days_overdue=N`.

Uso CLI:
    python3 deadline_scanner.py --vault ~/vault-tdah
    python3 deadline_scanner.py --vault ~/vault-tdah --level critical,urgent
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from intent_parser import parse_intent


URGENCY_LEVELS = ["critical", "urgent", "soon", "upcoming", "eventual", "distant"]


# @spec ATTN-001
def classify_urgency(deadline: datetime.date, now: datetime.datetime) -> tuple[str, dict]:
    """
    Classify a deadline into exactly one of 6 canonical levels (ATTN-001).
    Returns (level_name, time_info_dict).
    Overdue items are classified as 'critical' with is_overdue=True and days_overdue=N.
    """
    today = now.date()
    days_left = (deadline - today).days

    if days_left < 0:
        return "critical", {
            "days_overdue": -days_left,
            "is_overdue": True,
            "days_left": days_left,
        }

    if days_left == 0:
        deadline_dt = datetime.datetime.combine(deadline, datetime.time(23, 59, 59))
        hours_left = (deadline_dt - now).total_seconds() / 3600
        if hours_left < 4:
            return "critical", {"hours_left": round(hours_left, 1), "days_left": 0}
        return "urgent", {"hours_left": round(hours_left, 1), "days_left": 0}

    if days_left == 1:
        return "urgent", {"days_left": 1, "hours_left": None}

    if days_left <= 3:
        return "soon", {"days_left": days_left}

    if days_left <= 7:
        return "upcoming", {"days_left": days_left}

    if days_left <= 30:
        return "eventual", {"days_left": days_left}

    return "distant", {"days_left": days_left}


def scan_vault_deadlines(vault_path: Path) -> dict:
    """Scan all .md files in the vault, classify by urgency."""
    now = datetime.datetime.now()

    result = {level: [] for level in URGENCY_LEVELS}
    total_with_deadline = 0
    parse_errors = 0

    # Scan project folders for intents
    locations = ["01-Proyectos-Activos", "03-Areas"]
    for loc_name in locations:
        loc = vault_path / loc_name
        if not loc.exists():
            continue

        # Find all .md files recursively
        for md_file in loc.rglob("*.md"):
            if md_file.name.startswith("."):
                continue

            try:
                data = parse_intent(md_file)
            except Exception:
                parse_errors += 1
                continue

            deadline_str = data["frontmatter"].get("deadline")
            if not deadline_str:
                continue

            # Parse deadline
            try:
                deadline = datetime.datetime.strptime(
                    str(deadline_str).split("T")[0].split(" ")[0],
                    "%Y-%m-%d",
                ).date()
            except (ValueError, TypeError):
                continue

            # Skip if already completed
            estado = str(data["frontmatter"].get("estado", "")).lower()
            if estado in ("done", "completado", "archived"):
                continue

            total_with_deadline += 1

            level, time_info = classify_urgency(deadline, now)

            entry = {
                "id": data["id"],
                "title": data["title"],
                "path": data["path"],
                "deadline": deadline.isoformat(),
                "estado": estado,
                "prioridad": data["frontmatter"].get("prioridad"),
                "proyecto": data["frontmatter"].get("proyecto"),
                **time_info,
            }

            # Include the next physical action if available, and surface the
            # most recent shutdown timestamp as `last_shutdown` so consumers
            # can render "Last worked …" without re-parsing the note.
            if data.get("shutdown_notes"):
                first_sd = data["shutdown_notes"][0]
                entry["next_action"] = first_sd.get("next_action")
                entry["last_shutdown"] = first_sd.get("timestamp")

            result[level].append(entry)

    # Sort each level by urgency (most urgent first).
    # Within 'critical': overdue items first (sorted by days_overdue desc), then imminent (hours_left asc).
    for level in result:
        if level == "critical":
            result[level].sort(key=lambda x: (
                0 if x.get("is_overdue") else 1,
                -x.get("days_overdue", 0) if x.get("is_overdue") else x.get("hours_left", 999),
            ))
        else:
            result[level].sort(key=lambda x: x.get("days_left", 999))

    return {
        "scanned_at": now.isoformat(),
        "vault_path": str(vault_path),
        "total_intents_with_deadline": total_with_deadline,
        "parse_errors": parse_errors,
        "by_urgency": result,
        "counts": {level: len(items) for level, items in result.items()},
        "has_critical": len(result["critical"]) > 0,
    }


# @spec ATTN-007
def main():
    p = argparse.ArgumentParser(prog="deadline_scanner")
    p.add_argument("--vault", required=True)
    p.add_argument("--level", help="Filter to specific levels (comma-separated)")
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"❌ Vault not found: {vault}", file=sys.stderr)
        sys.exit(1)

    result = scan_vault_deadlines(vault)

    if args.level:
        wanted = set(args.level.split(","))
        result["by_urgency"] = {
            k: v for k, v in result["by_urgency"].items() if k in wanted
        }

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
