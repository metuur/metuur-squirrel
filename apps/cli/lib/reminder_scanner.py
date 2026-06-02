#!/usr/bin/env python3
"""
reminder_scanner.py — Scans all intents for reminder_date fields, classifies by proximity.

Returns two buckets:
  - active:      reminder_date today or in the past, no suppression
  - approaching: reminder_date 1–7 calendar days in the future, no suppression

Suppression rules (R-2.2–R-2.4):
  - estado: done / completado / archived  → excluded
  - reminder_dismissed set (non-empty)    → excluded permanently
  - reminder_snoozed_until set AND future → suppressed (snoozed)
  - reminder_snoozed_until set AND past   → no suppression (snooze expired)

Scans 01-Proyectos-Activos and 03-Areas (same as deadline_scanner).

Usage CLI:
    python3 reminder_scanner.py --vault ~/vault-squirrel
    python3 reminder_scanner.py --vault ~/vault-squirrel --pretty
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from intent_parser import parse_intent


def _parse_date_str(s: str) -> datetime.date | None:
    """Parse a YYYY-MM-DD date string, return None on failure."""
    if not s:
        return None
    try:
        return datetime.datetime.strptime(
            str(s).split("T")[0].split(" ")[0], "%Y-%m-%d"
        ).date()
    except (ValueError, TypeError):
        return None


def scan_vault_reminders(vault_path: Path) -> dict:
    """
    Scan all .md files in 01-Proyectos-Activos and 03-Areas for reminder_date.

    Returns:
        {
            "scanned_at": ISO timestamp string,
            "vault_path": str,
            "approaching": [{"id", "title", "path", "reminder_date", "project"}, ...],
            "active":      [{"id", "title", "path", "reminder_date", "project"}, ...],
        }
    """
    today = datetime.date.today()
    now = datetime.datetime.now()

    approaching: list[dict] = []
    active: list[dict] = []

    locations = ["01-Proyectos-Activos", "03-Areas"]
    for loc_name in locations:
        loc = vault_path / loc_name
        if not loc.exists():
            continue

        for md_file in loc.rglob("*.md"):
            if md_file.name.startswith("."):
                continue

            try:
                data = parse_intent(md_file)
            except Exception:
                continue

            fm = data["frontmatter"]

            # R-2.2: skip done/completado/archived
            estado = str(fm.get("status", "")).lower()
            if estado in ("done", "completed", "archived"):
                continue

            # Must have reminder_date
            reminder_date_str = fm.get("reminder_date")
            if not reminder_date_str:
                continue

            reminder_date = _parse_date_str(str(reminder_date_str))
            if reminder_date is None:
                continue

            # R-2.3: skip if reminder_dismissed is set (any non-empty value)
            dismissed = str(fm.get("reminder_dismissed", "")).strip()
            if dismissed:
                continue

            # R-2.4: skip if reminder_snoozed_until is set AND in the future
            snoozed_str = str(fm.get("reminder_snoozed_until", "")).strip()
            if snoozed_str:
                snoozed_until = _parse_date_str(snoozed_str)
                if snoozed_until is not None and snoozed_until > today:
                    continue
                # If snoozed_until is past or unparseable, treat as no suppression

            entry = {
                "id": data["id"],
                "title": data["title"],
                "path": data["path"],
                "reminder_date": reminder_date.isoformat(),
                "project": fm.get("project"),
            }

            days_ahead = (reminder_date - today).days

            # R-2.5: reminder_date today or in the past → active
            if days_ahead <= 0:
                active.append(entry)
            # R-2.6: reminder_date 1–7 days in the future → approaching
            elif 1 <= days_ahead <= 7:
                approaching.append(entry)
            # else: > 7 days in future → excluded from output

    # Sort active: most overdue first (earliest reminder_date first)
    active.sort(key=lambda x: x["reminder_date"])
    # Sort approaching: soonest first
    approaching.sort(key=lambda x: x["reminder_date"])

    return {
        "scanned_at": now.isoformat(),
        "vault_path": str(vault_path),
        "approaching": approaching,
        "active": active,
    }


def main():
    p = argparse.ArgumentParser(prog="reminder_scanner")
    p.add_argument("--vault", required=True)
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"Vault not found: {vault}", file=sys.stderr)
        sys.exit(1)

    result = scan_vault_reminders(vault)

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
