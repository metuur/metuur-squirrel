#!/usr/bin/env python3
import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from focus_picker import get_manual_focus, set_manual_focus, clear_manual_focus, IntentNotFound  # noqa: E402
import db  # noqa: E402


def main():
    p = argparse.ArgumentParser(prog="focus_cli")
    subs = p.add_subparsers(dest="cmd", required=True)

    get_p = subs.add_parser("get")
    get_p.add_argument("--vault", required=True)

    set_p = subs.add_parser("set")
    set_p.add_argument("--vault", required=True)
    set_p.add_argument("--slot", required=True, choices=["today", "today_pm", "week"])
    set_p.add_argument("--project", required=True)
    set_p.add_argument("--intent", required=True)

    clr_p = subs.add_parser("clear")
    clr_p.add_argument("--vault", required=True)
    clr_p.add_argument("--slot", required=True, choices=["today", "today_pm", "week"])

    ci_p = subs.add_parser("checkin")
    ci_p.add_argument("--vault", required=True)
    ci_p.add_argument("--project", required=True)
    ci_p.add_argument("--intent", required=True)
    ci_p.add_argument("--slot", required=True, choices=["today", "today_pm", "week"])

    co_p = subs.add_parser("checkout")
    co_p.add_argument("--vault", required=True)

    hist_p = subs.add_parser("history")
    hist_p.add_argument("--vault", required=True)
    hist_p.add_argument("--date")

    args = p.parse_args()
    vault = Path(args.vault)

    try:
        if args.cmd == "get":
            result = get_manual_focus(vault)
            print(json.dumps(result, default=str))

        elif args.cmd == "set":
            try:
                set_manual_focus(vault, args.slot, args.project, args.intent)
                print(json.dumps({"ok": True}))
            except IntentNotFound as e:
                print(json.dumps({"error": "intent_not_found", "slug": f"{e.project_slug}/{e.intent_slug}"}))
                sys.exit(1)

        elif args.cmd == "clear":
            clear_manual_focus(vault, args.slot)
            print(json.dumps({"ok": True}))

        elif args.cmd == "checkin":
            vault_key = Path(args.vault).name
            conn = db.get_conn()
            db.init_schema(conn)
            try:
                now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
                conn.execute(
                    "UPDATE work_sessions SET checkout_at = ? WHERE vault = ? AND checkout_at IS NULL",
                    (now_utc, vault_key),
                )
                conn.commit()
                today_iso = datetime.date.today().isoformat()
                cur = conn.execute(
                    "INSERT INTO work_sessions (vault, slot, date, project_slug, intent_slug, checkin_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (vault_key, args.slot, today_iso, args.project, args.intent, now_utc),
                )
                conn.commit()
                session_id = cur.lastrowid
            finally:
                conn.close()
            print(json.dumps({"session_id": session_id}))

        elif args.cmd == "checkout":
            vault_key = Path(args.vault).name
            conn = db.get_conn()
            db.init_schema(conn)
            try:
                row = conn.execute(
                    "SELECT id, project_slug, intent_slug FROM work_sessions"
                    " WHERE vault = ? AND checkout_at IS NULL ORDER BY checkin_at DESC LIMIT 1",
                    (vault_key,),
                ).fetchone()
                if row is None:
                    print(json.dumps({"error": "no_open_session"}))
                    sys.exit(1)
                session_id, project_slug, intent_slug = row
                now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
                conn.execute(
                    "UPDATE work_sessions SET checkout_at = ? WHERE id = ?",
                    (now_utc, session_id),
                )
                conn.commit()
                duration_minutes = conn.execute(
                    "SELECT CAST((julianday(checkout_at) - julianday(checkin_at)) * 1440 AS INTEGER)"
                    " FROM work_sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()[0] or 0
                total = conn.execute(
                    "SELECT COALESCE(SUM(CAST((julianday(checkout_at) - julianday(checkin_at)) * 1440 AS INTEGER)), 0)"
                    " FROM work_sessions WHERE vault = ? AND project_slug = ? AND intent_slug = ? AND checkout_at IS NOT NULL",
                    (vault_key, project_slug, intent_slug),
                ).fetchone()[0]
                time_invested = int(total)
            finally:
                conn.close()
            vault_path = Path(args.vault)
            intent_file = vault_path / "01-Active-Projects" / project_slug / f"{intent_slug}.md"
            if intent_file.is_file():
                from intent_parser import write_frontmatter  # noqa: E402
                write_frontmatter(intent_file, {"time_invested_minutes": time_invested})
            print(json.dumps({
                "session_id": session_id,
                "duration_minutes": duration_minutes,
                "time_invested_minutes": time_invested,
            }))

        elif args.cmd == "history":
            vault_key = Path(args.vault).name
            date_str = args.date if args.date else datetime.date.today().isoformat()
            conn = db.get_conn()
            db.init_schema(conn)
            try:
                picks = conn.execute(
                    "SELECT id, vault, slot, date, project_slug, intent_slug, picked_at, cleared_at"
                    " FROM focus_picks WHERE vault = ? AND date = ? ORDER BY picked_at DESC",
                    (vault_key, date_str),
                ).fetchall()
                sessions = conn.execute(
                    "SELECT id, vault, slot, date, project_slug, intent_slug, checkin_at, checkout_at,"
                    " CASE WHEN checkout_at IS NOT NULL"
                    " THEN CAST((julianday(checkout_at) - julianday(checkin_at)) * 1440 AS INTEGER)"
                    " ELSE NULL END AS duration_minutes"
                    " FROM work_sessions WHERE vault = ? AND date = ? ORDER BY checkin_at DESC",
                    (vault_key, date_str),
                ).fetchall()
            finally:
                conn.close()
            pick_keys = ("id", "vault", "slot", "date", "project_slug", "intent_slug", "picked_at", "cleared_at")
            session_keys = ("id", "vault", "slot", "date", "project_slug", "intent_slug", "checkin_at", "checkout_at", "duration_minutes")
            print(json.dumps({
                "picks": [dict(zip(pick_keys, r)) for r in picks],
                "sessions": [dict(zip(session_keys, r)) for r in sessions],
            }))

    except Exception as e:
        print(json.dumps({"error": "unexpected", "detail": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
