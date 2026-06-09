#!/usr/bin/env python3
"""
quick_task_scanner.py — Scans the Quick Task Stack in SCRATCH-PAD, classifies by state.

Quick Tasks are markdown files in 01-Proyectos-Activos/SCRATCH-PAD/ carrying
`quick_task: true` in their frontmatter. This scanner is pure classification — it
never mutates files (the wake-commit that reactivates due snoozed tasks lives in the
writer, driven by the API handler).

Returns (R-2.1, R-2.2, R-2.6, R-2.7, R-4.1, R-4.5):
  {
    "scanned_at": ISO timestamp,
    "vault_path": str,
    "active":   [{"id", "text", "path", "qt_created_at"}, ...]   # oldest first (FIFO top)
    "snoozed":  [{"id", "text", "path", "qt_snoozed_until", "wake_due"}, ...]  # kept visible
    "active_count": int,
  }

Classification:
  qt_state == done (or status: done)            → excluded
  qt_state == active                            → active
  qt_state == snoozed, qt_snoozed_until > now   → snoozed (wake_due: False)
  qt_state == snoozed, qt_snoozed_until <= now  → snoozed (wake_due: True) — eligible to return

Usage CLI:
    python3 quick_task_scanner.py --vault ~/vault-squirrel
    python3 quick_task_scanner.py --vault ~/vault-squirrel --pretty
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from intent_parser import parse_intent

SCRATCH_PAD_DIR = Path("01-Proyectos-Activos") / "SCRATCH-PAD"


def _parse_dt(value) -> datetime.datetime | None:
    """Parse an ISO-8601 timestamp (date or datetime). Tolerates native date/datetime
    objects returned by the frontmatter parser. Returns None on failure."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day)
    s = str(value).strip()
    if not s:
        return None
    # Normalize a trailing Z and accept both "T" and " " separators.
    s = s.replace("Z", "")
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        # Fall back to date-only.
        try:
            return datetime.datetime.strptime(s.split("T")[0].split(" ")[0], "%Y-%m-%d")
        except ValueError:
            return None


def _is_quick_task(fm: dict) -> bool:
    """True when frontmatter marks the file as a Quick Task."""
    flag = fm.get("quick_task")
    if isinstance(flag, bool):
        return flag
    return str(flag).strip().lower() in ("true", "yes", "1")


def scan_quick_tasks(vault_path: Path) -> dict:
    """Scan SCRATCH-PAD for quick_task files and classify them."""
    now = datetime.datetime.now()

    active: list[dict] = []
    snoozed: list[dict] = []

    folder = vault_path / SCRATCH_PAD_DIR
    if folder.exists():
        for md_file in folder.rglob("*.md"):
            if md_file.name.startswith("."):
                continue

            try:
                data = parse_intent(md_file)
            except Exception:
                continue

            fm = data["frontmatter"]
            if not _is_quick_task(fm):
                continue

            # R-2.6: done is excluded from every bucket.
            qt_state = str(fm.get("qt_state", "")).strip().lower()
            status = str(fm.get("status", "")).strip().lower()
            if qt_state == "done" or status in ("done", "completed", "archived"):
                continue

            entry = {
                "id": data["id"],
                "text": data["title"],
                "path": data["path"],
            }

            if qt_state == "snoozed":
                snoozed_until = _parse_dt(fm.get("qt_snoozed_until"))
                entry["qt_snoozed_until"] = (
                    snoozed_until.isoformat() if snoozed_until else None
                )
                # R-4.1 / R-4.5: a snoozed task with no parseable wake time, or one
                # whose wake time has passed, is eligible to return.
                entry["wake_due"] = snoozed_until is None or snoozed_until <= now
                snoozed.append(entry)
            else:
                # Default (active) — includes files without an explicit qt_state.
                entry["qt_created_at"] = str(fm.get("qt_created_at", ""))
                active.append(entry)

    # R-2.1 / R-2.7: FIFO — oldest qt_created_at at the top.
    active.sort(key=lambda x: x["qt_created_at"])
    # Snoozed: soonest wake first (None wake times sort first as already-due).
    snoozed.sort(key=lambda x: x.get("qt_snoozed_until") or "")

    return {
        "scanned_at": now.isoformat(),
        "vault_path": str(vault_path),
        "active": active,
        "snoozed": snoozed,
        "active_count": len(active),
    }


def main():
    p = argparse.ArgumentParser(prog="quick_task_scanner")
    p.add_argument("--vault", required=True)
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"Vault not found: {vault}", file=sys.stderr)
        sys.exit(1)

    result = scan_quick_tasks(vault)
    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
