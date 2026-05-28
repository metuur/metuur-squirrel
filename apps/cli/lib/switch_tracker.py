#!/usr/bin/env python3
"""
switch_tracker.py — Registra context switches y calcula focus_score diario.

Usado por:
  - /cb-start (registra inicio de sesión sobre proyecto)
  - /cb-end (registra fin)
  - /cb-status (calcula focus_score)

Storage: <vault>/.squirrel/switches.jsonl (append-only, audit-friendly).

Uso CLI:
    python3 switch_tracker.py record --vault X --from A --to B
    python3 switch_tracker.py record --vault X --to A --reason session-start
    python3 switch_tracker.py status --vault X
    python3 switch_tracker.py status --vault X --date 2026-05-23
"""

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Optional


WIP_DAILY_BUDGET = 2  # max voluntary switches per day


def _switches_log_path(vault_path: Path) -> Path:
    log_dir = vault_path / ".squirrel"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "switches.jsonl"


# @spec ATTN-002, ATTN-008
def record_switch(
    vault_path: Path,
    to_context: str,
    from_context: Optional[str] = None,
    reason: str = "voluntary",
) -> dict:
    """Record a context switch."""
    log_path = _switches_log_path(vault_path)

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "date": datetime.date.today().isoformat(),
        "from": from_context,
        "to": to_context,
        "reason": reason,  # voluntary | emergency | session-start | session-end | override
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def read_switches(vault_path: Path, date_filter: Optional[str] = None) -> list[dict]:
    """Read switch log, optionally filtered by date (YYYY-MM-DD)."""
    log_path = _switches_log_path(vault_path)
    if not log_path.exists():
        return []

    entries = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if date_filter and entry.get("date") != date_filter:
                continue
            entries.append(entry)
    return entries


def compute_focus_score(switches: list[dict]) -> int:
    """
    Compute focus_score 0-100 from a day's switches.

    Formula:
      score = 100 - (voluntary_switches × 20)
      Each emergency switch = -5 (smaller penalty)
      Each override = -10
      Cap at [0, 100]
    """
    if not switches:
        return 100  # No switches = perfect focus

    voluntary = sum(1 for s in switches if s.get("reason") == "voluntary")
    emergency = sum(1 for s in switches if s.get("reason") == "emergency")
    override = sum(1 for s in switches if s.get("reason") == "override")

    score = 100 - (voluntary * 20) - (emergency * 5) - (override * 10)
    return max(0, min(100, score))


# @spec ATTN-005
def compute_focus_score_for_window(vault_path: Path, from_date: str, to_date: str) -> dict:
    """Compute focus score for a date window [from_date, to_date] inclusive."""
    all_switches = read_switches(vault_path)
    window_switches = [
        s for s in all_switches
        if from_date <= s.get("date", "") <= to_date
    ]
    return {
        "from_date": from_date,
        "to_date": to_date,
        "switches": len(window_switches),
        "focus_score": compute_focus_score(window_switches),
    }


def get_status(vault_path: Path, date: Optional[str] = None) -> dict:
    """Get switch status for a date (default today) plus week summary."""
    today = date or datetime.date.today().isoformat()

    today_switches = read_switches(vault_path, date_filter=today)

    # Count by type
    voluntary = [s for s in today_switches if s.get("reason") == "voluntary"]
    session_starts = [s for s in today_switches if s.get("reason") == "session-start"]
    contexts_today = sorted(set(
        s["to"] for s in today_switches if s.get("to")
    ))

    focus_score = compute_focus_score(today_switches)

    # Week summary (last 7 days)
    all_switches = read_switches(vault_path)
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    week_switches = [s for s in all_switches if s.get("date", "") >= week_ago]

    # Group by day
    by_day = {}
    for s in week_switches:
        d = s.get("date")
        if d:
            by_day.setdefault(d, []).append(s)

    days_scored = []
    for d, day_switches in sorted(by_day.items()):
        days_scored.append({
            "date": d,
            "switches": len([s for s in day_switches if s.get("reason") != "session-start"]),
            "focus_score": compute_focus_score(day_switches),
        })

    best_day = max(days_scored, key=lambda x: x["focus_score"], default=None)
    worst_day = min(days_scored, key=lambda x: x["focus_score"], default=None)

    return {
        "today": {
            "date": today,
            "voluntary_switches": len(voluntary),
            "session_starts": len(session_starts),
            "total_entries": len(today_switches),
            "budget": WIP_DAILY_BUDGET,
            "over_budget": len(voluntary) > WIP_DAILY_BUDGET,
            "focus_score": focus_score,
            "contexts": contexts_today,
        },
        "this_week": {
            "days_with_data": len(days_scored),
            "total_switches": sum(d["switches"] for d in days_scored),
            "avg_focus_score": round(
                sum(d["focus_score"] for d in days_scored) / len(days_scored), 1
            ) if days_scored else None,
            "best_day": best_day,
            "worst_day": worst_day,
            "by_day": days_scored,
        },
    }


def main():
    p = argparse.ArgumentParser(prog="switch_tracker")
    subs = p.add_subparsers(dest="cmd", required=True)

    rec = subs.add_parser("record", help="Record a switch event")
    rec.add_argument("--vault", required=True)
    rec.add_argument("--from", dest="from_context", default=None)
    rec.add_argument("--to", dest="to_context", required=True)
    rec.add_argument(
        "--reason",
        choices=["voluntary", "emergency", "session-start", "session-end", "override"],
        default="voluntary",
    )

    stat = subs.add_parser("status", help="Get focus status")
    stat.add_argument("--vault", required=True)
    stat.add_argument("--date", help="YYYY-MM-DD (default: today)")
    stat.add_argument("--from-date", dest="from_date", help="Window start YYYY-MM-DD")
    stat.add_argument("--to-date", dest="to_date", help="Window end YYYY-MM-DD")
    stat.add_argument("--pretty", action="store_true")

    args = p.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"❌ Vault not found: {vault}", file=sys.stderr)
        sys.exit(1)

    if args.cmd == "record":
        entry = record_switch(
            vault,
            to_context=args.to_context,
            from_context=args.from_context,
            reason=args.reason,
        )
        print(json.dumps(entry, indent=2))
    elif args.cmd == "status":
        if args.from_date and args.to_date:
            result = compute_focus_score_for_window(vault, args.from_date, args.to_date)
        else:
            result = get_status(vault, date=args.date)
        indent = 2 if getattr(args, "pretty", False) else None
        print(json.dumps(result, indent=indent, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
