#!/usr/bin/env python3
"""where_am_i_formatter.py — Full "¿en qué estaba?" render in one call.

Replaces the multi-step Bash workflow that used to live in
skills/where-am-i/SKILL.md. Resolves the vault, runs the aggregator,
switch tracker, and deadline scanner, and prints the final human text
to stdout. The skill prints stdout verbatim — zero formatting tokens.

Exit codes:
  0  success (output already printed)
  2  no config / no default vault (message on stderr)
  3  vault not found on disk (message on stderr)
  4  named vault unknown (message on stderr)
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from typing import Any, Optional

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config_loader import ConfigError, VaultNotFoundError, get_vault  # noqa: E402
from status_aggregator import aggregate_status  # noqa: E402
from switch_tracker import get_status as switch_status  # noqa: E402

try:
    from deadline_scanner import scan_vault_deadlines  # noqa: E402
except Exception:  # pragma: no cover — optional component
    scan_vault_deadlines = None  # type: ignore[assignment]


def _resolve_vault(name: Optional[str]) -> pathlib.Path:
    try:
        vault = get_vault(name=name)
    except VaultNotFoundError as e:
        print(f"VAULT_UNKNOWN: {e}", file=sys.stderr)
        sys.exit(4)
    except ConfigError as e:
        print(f"NO_CONFIG: {e}", file=sys.stderr)
        sys.exit(2)
    path = pathlib.Path(vault.path).expanduser().resolve()
    if not path.exists():
        print(f"VAULT_MISSING: {path}", file=sys.stderr)
        sys.exit(3)
    return path


def _format_alerts(alerts: list[dict]) -> list[str]:
    if not alerts:
        return []
    out = ["🚨 ATENCIÓN:"]
    for a in alerts[:3]:
        proj = a.get("project") or "global"
        out.append(f"  • [{a.get('level','?')}] {proj}: {a.get('message','')}")
    return out


def _format_deadlines(by_urgency: dict) -> list[str]:
    critical = list(by_urgency.get("critical", []) or [])
    urgent = list(by_urgency.get("urgent", []) or [])
    if not critical and not urgent:
        return []
    out = ["⏰ DEADLINES CRÍTICOS:"]
    shown = 0
    for item in critical:
        if shown >= 5:
            break
        title = item.get("title", "")
        item_id = item.get("id", "?")
        if item.get("is_overdue"):
            days = item.get("days_overdue", "?")
            out.append(f"  🔴 [{item_id}] — {title} — OVERDUE ({days}d)")
        else:
            hours = item.get("hours_left", "?")
            out.append(f"  🔴 [{item_id}] — {title} — HOY ({hours}h left)")
        shown += 1
    for item in urgent:
        if shown >= 5:
            break
        title = item.get("title", "")
        item_id = item.get("id", "?")
        hours = item.get("hours_left")
        tail = f"mañana / {hours}h" if hours is not None else "mañana"
        out.append(f"  🟠 [{item_id}] — {title} — {tail}")
        shown += 1
    total = len(critical) + len(urgent)
    if total > shown:
        out.append(f"  (+{total - shown} más)")
    out.append("Para ver todos: `/sq-deadlines`")
    return out


def _pick_recommendation(agg: dict) -> Optional[dict]:
    rec = agg.get("recommended_focus")
    if rec and rec.get("project"):
        return rec
    projects = (agg.get("wip") or {}).get("projects", []) or []
    with_activity = [p for p in projects if p.get("last_activity")]
    if with_activity:
        with_activity.sort(key=lambda x: x["last_activity"], reverse=True)
        top = with_activity[0]
        return {
            "project": top["id"],
            "intent": top.get("active_intent"),
            "reason": "actividad más reciente",
            "next_action": top.get("next_physical_action"),
        }
    if projects:
        top = projects[0]
        return {
            "project": top["id"],
            "intent": top.get("active_intent"),
            "reason": "primer proyecto WIP",
            "next_action": top.get("next_physical_action"),
        }
    return None


def _format_recommendation(rec: Optional[dict]) -> list[str]:
    out = ["🎯 Recomendación de foco AHORA (exactamente una):"]
    if not rec:
        out.append("  (sin proyectos WIP — usá /sq-init para crear el primero)")
        return out
    out.append(f"  Proyecto: {rec.get('project','?')}")
    out.append(f"  Intent: {rec.get('intent') or '(sin intent activo)'}")
    out.append(f"  Razón: {rec.get('reason') or 'proyecto con actividad más reciente'}")
    out.append(f"  Next action: {rec.get('next_action') or 'retomar desde el último shutdown note'}")
    return out


def _format_wip(projects: list[dict]) -> list[str]:
    if not projects:
        return []
    out = ["📋 Tus proyectos WIP:"]
    for p in projects:
        pct = p.get("percent_done", 0)
        days = p.get("days_since_activity")
        activity = f"hace {days} días" if days is not None else "sin actividad registrada"
        out.append(f"  {p.get('id','?')} ({pct}% | última actividad: {activity})")
        out.append(f"    Active: {p.get('active_intent') or '—'}")
        out.append(f"    Next: {p.get('next_physical_action') or '—'}")
    return out


def render(agg: dict, switch: dict, deadlines: Optional[dict]) -> str:
    wip = agg.get("wip") or {}
    parking = agg.get("parking_lot") or {}
    areas = agg.get("areas") or {}
    today = (switch or {}).get("today") or {}

    if (wip.get("count") or 0) == 0 and (parking.get("count") or 0) == 0:
        return "Tu vault está vacío. ¿Querés que ayude a crear el primer proyecto? (sí / no)\n"

    lines: list[str] = ["📊 ¿En qué estabas?", ""]
    lines.append(
        f"Estado del vault: {wip.get('count',0)}/{wip.get('max','?')} WIP, "
        f"{parking.get('count',0)} parking, {areas.get('count',0)} áreas"
    )
    lines.append(
        f"Focus de hoy: {today.get('focus_score','?')}/100 "
        f"({today.get('voluntary_switches','?')} switches)"
    )
    lines.append("")

    alert_lines = _format_alerts(agg.get("alerts") or [])
    if alert_lines:
        lines.extend(alert_lines)
        lines.append("")

    if deadlines:
        ddl_lines = _format_deadlines(deadlines.get("by_urgency") or {})
        if ddl_lines:
            lines.extend(ddl_lines)
            lines.append("")

    rec = _pick_recommendation(agg)
    lines.extend(_format_recommendation(rec))
    lines.append("")

    wip_lines = _format_wip(wip.get("projects") or [])
    if wip_lines:
        lines.extend(wip_lines)
        lines.append("")

    if today.get("over_budget"):
        lines.append(
            f"⚠️ Excediste budget de switches hoy "
            f"({today.get('voluntary_switches','?')} > {today.get('budget','?')})."
        )
        lines.append("   Considerá no cambiar más de proyecto hoy.")
        lines.append("")

    if rec and rec.get("project"):
        lines.append(f"¿Hacemos `/sq-start {rec['project']}` para retomar? (sí / otro)")
    else:
        lines.append("¿Empezamos? (sí / otro)")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    p = argparse.ArgumentParser(prog="where_am_i_formatter")
    p.add_argument("--name", default=None, help="Vault name (omit for default)")
    args = p.parse_args()

    vault_path = _resolve_vault(args.name)

    agg = aggregate_status(vault_path)
    switch = switch_status(vault_path)
    deadlines: Optional[dict[str, Any]] = None
    if scan_vault_deadlines is not None:
        try:
            deadlines = scan_vault_deadlines(vault_path)
        except Exception:
            deadlines = None

    sys.stdout.write(render(agg, switch, deadlines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
