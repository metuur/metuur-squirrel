#!/usr/bin/env python3
"""
dashboard_generator.py — Generates a single-file HTML dashboard from vault data.

No external dependencies. Embeds all CSS. Reads status + deadlines and renders
a static HTML file that can be opened in any browser.

Uso CLI:
    python3 dashboard_generator.py --vault ~/vault-squirrel
    python3 dashboard_generator.py --vault ~/vault-squirrel --out ~/dashboard.html
    python3 dashboard_generator.py --vault ~/vault-squirrel --open
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from status_aggregator import aggregate_status
from deadline_scanner import scan_vault_deadlines

_URGENCY_ORDER = ["critical", "urgent", "soon", "upcoming", "eventual", "distant"]
_URGENCY_COLOR = {
    "critical": "#dc2626",
    "urgent": "#f97316",
    "soon": "#eab308",
    "upcoming": "#3b82f6",
    "eventual": "#22c55e",
    "distant": "#6b7280",
}
_URGENCY_ICON = {
    "critical": "🔴",
    "urgent": "🟠",
    "soon": "🟡",
    "upcoming": "🔵",
    "eventual": "🟢",
    "distant": "⚪",
}


def _esc(s: str) -> str:
    return (str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def _deadline_rows(by_urgency: dict) -> str:
    rows = []
    for lvl in _URGENCY_ORDER:
        items = by_urgency.get(lvl, [])
        for item in items:
            color = _URGENCY_COLOR[lvl]
            icon = _URGENCY_ICON[lvl]
            tag = _esc(item.get("id", "?"))
            title = _esc(item.get("title", ""))
            dl = _esc(item.get("deadline", ""))
            days = item.get("days_left")
            hrs = item.get("hours_left")
            if item.get("is_overdue"):
                overdue_days = item.get("days_overdue", 0)
                time_str = f"{overdue_days}d overdue" if overdue_days else "OVERDUE"
            elif hrs is not None and hrs < 24:
                time_str = f"{hrs}h left"
            elif days is not None:
                time_str = f"{days}d left"
            else:
                time_str = ""
            rows.append(
                f'<tr>'
                f'<td><span class="badge" style="background:{color}">{icon} {lvl.upper()}</span></td>'
                f'<td class="tag">{tag}</td>'
                f'<td>{title}</td>'
                f'<td>{dl}</td>'
                f'<td class="time-left">{_esc(time_str)}</td>'
                f'</tr>'
            )
    return "\n".join(rows) if rows else '<tr><td colspan="5" class="empty">No deadlines found.</td></tr>'


def _wip_cards(projects: list) -> str:
    if not projects:
        return '<p class="empty">No WIP projects.</p>'
    cards = []
    for p in projects:
        pid = _esc(p.get("id", "?"))
        pct = p.get("intents", {}).get("percent_done", 0)
        dl = _esc(p.get("deadline", "—"))
        last = _esc(p.get("active_intent", ""))
        bar_w = max(2, pct)
        cards.append(
            f'<div class="card">'
            f'  <div class="card-title">{pid}</div>'
            f'  <div class="progress-bar"><div class="progress-fill" style="width:{bar_w}%"></div></div>'
            f'  <div class="card-meta">{pct}% done &nbsp;·&nbsp; deadline: {dl}</div>'
            f'  <div class="card-meta last-intent">Last: {last}</div>'
            f'</div>'
        )
    return "\n".join(cards)


def _alert_rows(alerts: list) -> str:
    if not alerts:
        return ""
    rows = []
    for a in alerts:
        lvl = a.get("level", "info")
        color = {"critical": "#ef4444", "warning": "#f97316", "info": "#3b82f6"}.get(lvl, "#6b7280")
        proj = _esc(a.get("project") or "global")
        msg = _esc(a.get("message", ""))
        rows.append(
            f'<div class="alert-row" style="border-left:4px solid {color}">'
            f'  <strong>{proj}</strong>: {msg}'
            f'  <span class="badge" style="background:{color}">{lvl}</span>'
            f'</div>'
        )
    return "\n".join(rows)


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #0f172a; color: #e2e8f0; padding: 24px; }
h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
h2 { font-size: 1rem; font-weight: 600; color: #94a3b8; margin: 24px 0 12px; text-transform: uppercase; letter-spacing: .05em; }
.subtitle { color: #64748b; font-size: .875rem; margin-bottom: 24px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
@media (max-width: 800px) { .grid { grid-template-columns: 1fr; } }
.section { background: #1e293b; border-radius: 12px; padding: 20px; }
.card { background: #0f172a; border-radius: 8px; padding: 14px; margin-bottom: 10px; }
.card:last-child { margin-bottom: 0; }
.card-title { font-weight: 600; font-size: 1rem; margin-bottom: 8px; }
.card-meta { font-size: .8rem; color: #64748b; margin-top: 4px; }
.last-intent { font-style: italic; }
.progress-bar { background: #334155; border-radius: 4px; height: 6px; margin: 8px 0; }
.progress-fill { background: #3b82f6; border-radius: 4px; height: 6px; transition: width .3s; }
table { width: 100%; border-collapse: collapse; font-size: .875rem; }
th { text-align: left; padding: 8px 10px; background: #0f172a; color: #64748b;
     font-weight: 600; text-transform: uppercase; font-size: .75rem; letter-spacing: .04em; }
td { padding: 8px 10px; border-bottom: 1px solid #1e293b; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #1e293b; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: .7rem;
         font-weight: 700; color: #fff; white-space: nowrap; }
.tag { font-family: monospace; font-size: .8rem; color: #a5f3fc; }
.time-left { font-size: .8rem; color: #94a3b8; }
.empty { color: #475569; font-style: italic; text-align: center; padding: 20px; }
.focus-box { background: #1e3a5f; border: 1px solid #3b82f6; border-radius: 10px;
             padding: 16px; margin-bottom: 24px; }
.focus-project { font-size: 1.1rem; font-weight: 700; color: #60a5fa; }
.focus-reason { color: #94a3b8; font-size: .875rem; margin-top: 4px; }
.focus-next { color: #e2e8f0; font-size: .9rem; margin-top: 8px; }
.alert-row { padding: 10px 14px; background: #1e293b; border-radius: 6px;
             margin-bottom: 8px; font-size: .875rem; display: flex;
             justify-content: space-between; align-items: center; gap: 10px; }
.ts { color: #475569; font-size: .75rem; }
"""


def generate_html(vault_path: Path) -> str:
    status = aggregate_status(vault_path)
    deadlines = scan_vault_deadlines(vault_path)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    wip = status.get("wip", {})
    projs = wip.get("projects", [])
    alerts = status.get("alerts", [])
    focus = status.get("recommended_focus") or {}
    by_urgency = deadlines.get("by_urgency", {})
    total_dl = deadlines.get("total_intents_with_deadline", 0)

    focus_html = ""
    if focus:
        proj = _esc(focus.get("project", ""))
        reason = _esc(focus.get("reason", ""))
        nxt = _esc(focus.get("next_action", ""))
        focus_html = (
            f'<div class="focus-box">'
            f'  <div class="focus-project">🎯 {proj}</div>'
            f'  <div class="focus-reason">{reason}</div>'
            + (f'  <div class="focus-next">→ {nxt}</div>' if nxt else "")
            + f'</div>'
        )

    alerts_html = _alert_rows(alerts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>Context Bridge Dashboard</title>
<style>{_CSS}</style>
</head>
<body>
<h1>🧠 Context Bridge</h1>
<p class="subtitle ts">Vault: {_esc(str(vault_path))} &nbsp;·&nbsp; Generated: {now_str} &nbsp;·&nbsp; Auto-refreshes every 5 min</p>

{focus_html}

{"<div class='section' style='margin-bottom:24px'><h2>⚠️ Alerts</h2>" + alerts_html + "</div>" if alerts_html else ""}

<div class="grid">
  <div class="section">
    <h2>🟢 WIP ({len(projs)}/{wip.get('max', 3)})</h2>
    {_wip_cards(projs)}
  </div>
  <div class="section">
    <h2>📦 Parking Lot ({status.get('parking_lot', {}).get('count', 0)})</h2>
    {"".join(f'<div class="card"><div class="card-title">{_esc(p.get("id", str(p)) if isinstance(p, dict) else str(p))}</div></div>' for p in status.get("parking_lot", {}).get("items", [])) or '<p class="empty">Empty.</p>'}
  </div>
</div>

<div class="section" style="margin-top:24px">
  <h2>📅 Deadlines ({total_dl} total)</h2>
  <table>
    <thead><tr><th>Level</th><th>ID</th><th>Title</th><th>Deadline</th><th>Remaining</th></tr></thead>
    <tbody>
      {_deadline_rows(by_urgency)}
    </tbody>
  </table>
</div>

</body>
</html>"""


def main():
    p = argparse.ArgumentParser(prog="dashboard_generator",
                                description="Generate HTML dashboard from vault data")
    p.add_argument("--vault", required=True, help="Path to vault root")
    p.add_argument("--out", help="Output HTML file (default: ~/.squirrel/dashboard.html)")
    p.add_argument("--open", action="store_true", dest="open_browser",
                   help="Open the dashboard in the default browser after generating")
    args = p.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"❌ Vault not found: {vault}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out).expanduser() if args.out else \
               Path("~/.squirrel/dashboard.html").expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = generate_html(vault)
    out_path.write_text(html, encoding="utf-8")
    print(f"✅  Dashboard written to: {out_path}")

    if args.open_browser:
        import subprocess
        subprocess.run(["open", str(out_path)], check=False)


if __name__ == "__main__":
    main()
