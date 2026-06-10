#!/usr/bin/env python3
"""
status_aggregator.py — Aggregator central del estado del vault.

Reemplaza ~3000 tokens de lectura del LLM con una llamada de script
que devuelve un JSON estructurado.

Usado por skills: where-am-i, status, brief, session-start.

Uso CLI:
    python3 status_aggregator.py --vault ~/vault-squirrel
    python3 status_aggregator.py --vault ~/vault-squirrel --project TEST-PROJECT
    python3 status_aggregator.py --vault ~/vault-squirrel --output json --detailed
"""

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Optional

# Import sibling
sys.path.insert(0, str(Path(__file__).parent))
from intent_parser import parse_intent, parse_frontmatter


def _is_quick_task_file(md: Path) -> bool:
    """True when an .md file is a Quick Task (R-6.1: not an intent).

    Quick Tasks live in SCRATCH-PAD but must never be counted as intents/WIP.
    """
    try:
        fm, _ = parse_frontmatter(md.read_text(encoding="utf-8"))
    except Exception:
        return False
    if str(fm.get("type", "")).strip().lower() == "quick_task":
        return True
    return str(fm.get("quick_task", "")).strip().lower() in ("true", "yes", "1")

# @spec VAULT-008

# ─────────────────────────────────────────────────────────────────────────────
# Vault scanning
# ─────────────────────────────────────────────────────────────────────────────

def find_projects(vault_path: Path) -> dict[str, list[Path]]:
    """
    Find all projects in the vault, grouped by location.
    Returns dict with keys: wip, parking, areas, archive.
    """
    projects = {
        "wip": [],
        "parking": [],
        "areas": [],
        "archive": [],
    }

    locations = {
        "01-Active-Projects": "wip",
        "02-Parking-Lot": "parking",
        "03-Areas": "areas",
        "06-Archive": "archive",
    }

    for folder_name, category in locations.items():
        folder = vault_path / folder_name
        if not folder.exists():
            continue

        # Each project is a subfolder OR a top-level .md file
        for item in folder.iterdir():
            if item.is_dir():
                # Project page is the file named like the folder
                project_md = item / f"{item.name}.md"
                if project_md.exists():
                    projects[category].append(project_md)
                else:
                    # Fallback: first .md file
                    md_files = sorted(item.glob("*.md"))
                    if md_files:
                        projects[category].append(md_files[0])
            elif item.suffix == ".md" and not item.name.startswith("."):
                # Top-level .md (mostly for Areas)
                projects[category].append(item)

    return projects


def find_intents_for_project(project_md_path: Path) -> list[Path]:
    """Find all intent files in a project's folder (excluding the Project Page)."""
    project_folder = project_md_path.parent
    project_name = project_md_path.stem

    intents = []
    for md in project_folder.glob("*.md"):
        if md.name == project_md_path.name:
            continue  # skip the project page itself
        if md.name.startswith("."):
            continue
        if _is_quick_task_file(md):
            continue  # R-6.1: Quick Tasks are not intents
        intents.append(md)

    return sorted(intents)


# ─────────────────────────────────────────────────────────────────────────────
# Active intent resolution
# ─────────────────────────────────────────────────────────────────────────────

def active_intent_for(vault: Path, project_slug: str) -> Optional[str]:
    """
    Return the active intent slug for a project, or None if no intent has activity yet.

    "Active" = the intent (in the project's folder) whose most recent shutdown note
    has the most recent timestamp. Mirrors the logic already used by analyze_project()
    around status_aggregator.py:163–181.

    - vault: Path to the vault root.
    - project_slug: the project's TAG / folder name (e.g. "MY-PROJECT").
    - Returns: the intent's file stem (e.g. "MY-PROJECT-i01") or None if no intents
      have any shutdown notes / activity.
    """
    project_folder = vault / "01-Active-Projects" / project_slug
    if not project_folder.exists():
        return None

    project_md = project_folder / f"{project_slug}.md"
    intent_paths = find_intents_for_project(project_md)

    intents_with_activity = []
    for ip in intent_paths:
        try:
            intent = parse_intent(ip)
        except Exception:
            continue
        notes = intent.get("shutdown_notes") or []
        if notes and notes[0].get("timestamp"):
            intents_with_activity.append(intent)

    if not intents_with_activity:
        return None

    intents_with_activity.sort(
        key=lambda x: x["shutdown_notes"][0]["timestamp"],
        reverse=True,
    )
    return intents_with_activity[0]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# Project analysis
# ─────────────────────────────────────────────────────────────────────────────

def analyze_project(project_md_path: Path, detailed: bool = False) -> dict:
    """Build a structured summary of a project."""
    # Parse the project page
    try:
        page = parse_intent(project_md_path)
    except Exception as e:
        return {
            "id": project_md_path.stem,
            "path": str(project_md_path),
            "error": str(e),
        }

    project_id = page["id"]
    project_fm = page["frontmatter"]
    project_sections = page.get("sections", {})

    # Find all intents in the same folder
    intent_paths = find_intents_for_project(project_md_path)

    intents = []
    for ip in intent_paths:
        try:
            intent = parse_intent(ip)
            entry = {
                "id": intent["id"],
                "title": intent.get("title", ""),
                "path": intent["path"],
                "status": intent["frontmatter"].get("status", "unknown"),
                "priority": intent["frontmatter"].get("priority"),
                "deadline": intent["frontmatter"].get("deadline"),
                "days_to_deadline": intent["stats"]["days_to_deadline"],
                "days_since_activity": intent["stats"]["days_since_activity"],
                "percent_done": intent["stats"]["definition_of_done"]["percent_done"],
                "last_shutdown_note": intent["shutdown_notes"][0] if intent["shutdown_notes"] else None,
            }
            if detailed:
                s = intent.get("sections", {})
                entry["shutdown_notes"] = intent["shutdown_notes"]
                entry["dod_done"] = intent["stats"]["definition_of_done"]["done"]
                entry["dod_pending"] = intent["stats"]["definition_of_done"]["pending"]
                entry["open_questions"] = s.get("open_questions", "")
                entry["decisions"] = s.get("decisions", "")
                entry["intent_text"] = s.get("intent", "")
            intents.append(entry)
        except Exception as e:
            intents.append({"id": ip.stem, "path": str(ip), "error": str(e)})

    # Compute aggregates
    by_state = {"done": [], "in-progress": [], "pending": [], "blocked": [], "other": []}
    for it in intents:
        st = it.get("status", "pending").lower()
        if st in ("done", "completed"):
            by_state["done"].append(it["id"])
        elif st in ("in-progress", "wip", "in_progress"):
            by_state["in-progress"].append(it["id"])
        elif st in ("pending", "todo"):
            by_state["pending"].append(it["id"])
        elif st in ("blocked", "blocked"):
            by_state["blocked"].append(it["id"])
        else:
            by_state["other"].append(it["id"])

    total = len(intents)
    done_count = len(by_state["done"])
    percent_done = int(100 * done_count / total) if total > 0 else 0

    # Find active intent (most recent activity)
    active_intent = None
    last_activity = None
    days_since_activity = None
    next_action = None

    intents_with_activity = [
        it for it in intents
        if it.get("last_shutdown_note") and it.get("last_shutdown_note", {}).get("timestamp")
    ]
    if intents_with_activity:
        intents_with_activity.sort(
            key=lambda x: x["last_shutdown_note"]["timestamp"],
            reverse=True,
        )
        active = intents_with_activity[0]
        active_intent = active["id"]
        last_activity = active["last_shutdown_note"]["timestamp"]
        days_since_activity = active.get("days_since_activity")
        next_action = active.get("last_shutdown_note", {}).get("next_action")

    # Fallback: if no intent has activity, use the Project Page's own shutdown notes
    if not last_activity and page.get("shutdown_notes"):
        page_note = page["shutdown_notes"][0]
        last_activity = page_note.get("timestamp")
        next_action = page_note.get("next_action")
        days_since_activity = page["stats"].get("days_since_activity")

    # Build alerts
    alerts = []

    # Stale + finishing-tax = critical
    if project_fm.get("priority") == "finishing-tax":
        if days_since_activity and days_since_activity > 7:
            alerts.append({
                "level": "critical",
                "message": f"FINISHING-TAX: {days_since_activity} días sin actividad",
            })

    # Deadline soon
    if project_fm.get("deadline"):
        # Reuse parse_intent's _parse_date logic by checking stats
        deadline_str = project_fm["deadline"]
        try:
            deadline = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()
            days = (deadline - datetime.date.today()).days
            if days < 0:
                alerts.append({
                    "level": "critical",
                    "message": f"DEADLINE PASADO hace {-days} días",
                })
            elif days < 7:
                alerts.append({
                    "level": "urgent",
                    "message": f"Deadline en {days} días",
                })
        except (ValueError, TypeError):
            pass

    result = {
        "id": project_id,
        "path": str(project_md_path),
        "type": project_fm.get("type"),
        "status": project_fm.get("status"),
        "delivered": str(project_fm.get("delivered", "")).strip().lower() in ("true", "1", "yes"),
        "priority": project_fm.get("priority"),
        "deadline": project_fm.get("deadline"),
        "stakeholders": project_fm.get("stakeholders", []),
        "tags": project_fm.get("tags", []),
        "intents": {
            "total": total,
            "done": done_count,
            "in_progress": len(by_state["in-progress"]),
            "pending": len(by_state["pending"]),
            "blocked": len(by_state["blocked"]),
            "percent_done": percent_done,
            "by_state": by_state,
        },
        "active_intent": active_intent,
        "last_activity": last_activity,
        "days_since_activity": days_since_activity,
        "next_physical_action": next_action,
        "alerts": alerts,
    }
    if detailed:
        result["objective"] = project_sections.get("objective", "")
        result["context_dump"] = project_sections.get("context_dump", "")
        result["open_questions"] = project_sections.get("open_questions", "")
        result["intent_list"] = intents  # full intent objects (with sections)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Main aggregator
# ─────────────────────────────────────────────────────────────────────────────

# @spec VAULT-001, VAULT-005
def aggregate_status(vault_path: Path, project_filter: Optional[str] = None, detailed: bool = False) -> dict:
    """Build the full status JSON."""
    projects_by_loc = find_projects(vault_path)

    wip_projects = []
    for p in projects_by_loc["wip"]:
        analysis = analyze_project(p, detailed=detailed)
        if project_filter and analysis["id"] != project_filter:
            continue
        wip_projects.append(analysis)

    parking_items = []
    for p in projects_by_loc["parking"]:
        try:
            page = parse_intent(p)
            parking_items.append({
                "id": page["id"],
                "path": page["path"],
                "type": page["frontmatter"].get("type"),
                "status": page["frontmatter"].get("status", "PARKING-LOT"),
            })
        except Exception:
            parking_items.append({"id": p.stem, "path": str(p)})

    areas_items = []
    for p in projects_by_loc["areas"]:
        try:
            page = parse_intent(p)
            areas_items.append({
                "id": page["id"],
                "path": page["path"],
                "frecuencia": page["frontmatter"].get("frecuencia"),
            })
        except Exception:
            areas_items.append({"id": p.stem, "path": str(p)})

    # Global alerts (aggregated from all projects)
    global_alerts = []
    for proj in wip_projects:
        for alert in proj.get("alerts", []):
            global_alerts.append({
                "project": proj["id"],
                "level": alert["level"],
                "message": alert["message"],
            })

    # WIP capacity check
    wip_count = len(projects_by_loc["wip"])
    wip_max = 3  # default; should come from config
    if wip_count > wip_max:
        global_alerts.append({
            "project": None,
            "level": "warning",
            "message": f"WIP excede el máximo: {wip_count} > {wip_max}",
        })

    # Recommended focus: simple heuristic
    recommended_focus = _recommend_focus(wip_projects)

    return {
        "schema_version": "001",
        "vault_path": str(vault_path),
        "scanned_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "wip": {
            "count": wip_count,
            "max": wip_max,
            "at_capacity": wip_count >= wip_max,
            "projects": wip_projects,
        },
        "parking_lot": {
            "count": len(parking_items),
            "items": parking_items,
        },
        "areas": {
            "count": len(areas_items),
            "items": areas_items,
        },
        "alerts": global_alerts,
        "recommended_focus": recommended_focus,
    }


def _recommend_focus(wip_projects: list[dict]) -> Optional[dict]:
    """
    Simple heuristic to recommend which project/intent to focus on.

    Priority order:
    1. Critical alert + active intent (e.g., finishing-tax stale)
    2. Deadline within 3 days
    3. Most recent activity
    """
    if not wip_projects:
        return None

    # Rule 1: critical alerts (project-level OR with intent)
    for proj in wip_projects:
        for alert in proj.get("alerts", []):
            if alert["level"] == "critical":
                return {
                    "project": proj["id"],
                    "intent": proj.get("active_intent"),
                    "reason": alert["message"],
                    "next_action": proj.get("next_physical_action"),
                }

    # Rule 2: deadline soon (any urgent)
    for proj in wip_projects:
        for alert in proj.get("alerts", []):
            if alert["level"] == "urgent":
                return {
                    "project": proj["id"],
                    "intent": proj.get("active_intent"),
                    "reason": alert["message"],
                    "next_action": proj.get("next_physical_action"),
                }

    # Rule 3: most recently active project
    recent = [p for p in wip_projects if p.get("last_activity")]
    if recent:
        recent.sort(key=lambda x: x["last_activity"], reverse=True)
        top = recent[0]
        return {
            "project": top["id"],
            "intent": top.get("active_intent"),
            "reason": "Proyecto con actividad más reciente",
            "next_action": top.get("next_physical_action"),
        }

    return None


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(prog="status_aggregator")
    p.add_argument("--vault", required=True, help="Path to vault root")
    p.add_argument("--project", help="Filter to a single project")
    p.add_argument("--detailed", action="store_true", help="Include section text (objective, context_dump, open_questions, per-intent detail)")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--field", help="Print only a specific top-level field")
    args = p.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"❌ Vault not found: {vault}", file=sys.stderr)
        sys.exit(1)

    result = aggregate_status(vault, project_filter=args.project, detailed=args.detailed)

    if args.field:
        if args.field not in result:
            print(f"❌ Field not found: {args.field}", file=sys.stderr)
            sys.exit(1)
        result = result[args.field]

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
