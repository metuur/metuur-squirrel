#!/usr/bin/env python3
"""vault_migrator.py — migrate an existing Obsidian vault into squirrel-vault format.

Two-phase, copy-only. The source vault is NEVER modified.

    plan  — read-only scan of the source vault; produces a migration plan
            (JSON) mapping every source note to its squirrel target.
    apply — executes a saved plan: writes converted notes into the target
            vault. Never overwrites existing files (skips + reports).

Mapping heuristics (task: docs/tasks/obsidian-vault-migration-skill.md):
  - top-level folder with notes      -> project under 02-Parking-Lot/ (default)
                                        or 01-Proyectos-Activos/ (--dest active)
  - folder-note (Foo/Foo.md)         -> becomes the project page body
  - other notes in the folder        -> intents <TAG>-NOTE-NNN.md (flattened)
  - daily-notes folder               -> copied as-is into 04-Daily/
  - loose notes at the vault root    -> captures 99-Resources/Inbox/UNFILED-NNN.md
                                        (continues existing numbering)
  - non-markdown files               -> 99-Resources/Obsidian-Attachments/<relpath>
                                        (Obsidian wikilinks resolve by filename)
  - skipped: hidden dirs, .obsidian, .trash, .squirrel

Public API:

    build_plan(source: Path, vault_path: Path, dest_bucket: str) -> dict
    apply_plan(plan: dict) -> dict
    format_plan(plan: dict) -> str

CLI exit codes:
  0  success
  2  NO_CONFIG        no config / no default vault
  3  VAULT_MISSING    vault path on disk is missing
  4  VAULT_UNKNOWN    named vault not found
  5  SOURCE_INVALID   source missing, equal to target, or already a squirrel vault
  6  PLAN_INVALID     plan file missing or malformed
  7  NOTHING_TO_MIGRATE
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import re
import shutil
import sys
from typing import Optional

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from intent_parser import parse_frontmatter  # noqa: E402

_PROJECT_TAG_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$")
_DATE_STEM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")
_DAILY_NAME_RE = re.compile(r"daily|diario", re.IGNORECASE)
_H1_RE = re.compile(r"^# ", re.MULTILINE)

_SKIP_DIRS = {".obsidian", ".trash", ".squirrel"}
_ACTIVE_BUCKET = "01-Proyectos-Activos"
_PARKING_BUCKET = "02-Parking-Lot"

# Frontmatter keys the migrator owns; original values for these are replaced
# (normalized), everything else is passed through verbatim.
_OWNED_KEYS = {"id", "project", "status", "created", "tags", "type", "migrated_from"}

_STATUS_MAP = {
    "done": "done", "completed": "done", "complete": "done", "closed": "done",
    "in-progress": "in-progress", "in_progress": "in-progress", "doing": "in-progress",
    "active": "in-progress", "wip": "in-progress",
    "blocked": "blocked", "waiting": "blocked", "on-hold": "blocked",
}

_CODE_TO_EXIT = {
    "NO_CONFIG": 2,
    "VAULT_MISSING": 3,
    "VAULT_UNKNOWN": 4,
    "SOURCE_INVALID": 5,
    "PLAN_INVALID": 6,
    "NOTHING_TO_MIGRATE": 7,
}

_PROJECT_PAGE_BODY = """
# {name}

Migrated from Obsidian folder `{source_dir}`.

## 🎯 Objective
<What you want to achieve with this project and why it matters.>

## ✅ Definition of Done
- [ ] <Concrete, verifiable criterion>

## 🧩 Intents
<!-- Intents live as sibling files `<TAG>-NOTE-NNN.md` -->

## 📝 Context
<Background info, links, decisions>
"""


class MigrationError(Exception):
    """Raised when plan/apply cannot proceed. Carries a stable error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ─────────────────────────────────────────────────────────────────────────────
# Plan
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_tag(name: str) -> Optional[str]:
    tag = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").upper()
    tag = re.sub(r"-+", "-", tag)
    if not tag:
        return None
    if tag[0].isdigit():
        tag = "P" + tag
    return tag if _PROJECT_TAG_RE.match(tag) else None


def _map_status(raw) -> str:
    return _STATUS_MAP.get(str(raw or "").strip().lower(), "pending")


def _note_created(fm: dict, path: pathlib.Path) -> str:
    for key in ("created", "date"):
        val = str(fm.get(key) or "").strip()
        if val:
            try:
                return _dt.date.fromisoformat(val[:10]).isoformat()
            except ValueError:
                pass
    return _dt.date.fromtimestamp(path.stat().st_mtime).isoformat()


def _iter_md_files(folder: pathlib.Path) -> list[pathlib.Path]:
    """All .md files under folder, skipping hidden/system dirs. Sorted."""
    out = []
    for p in sorted(folder.rglob("*.md")):
        rel_parts = p.relative_to(folder).parts
        if any(part.startswith(".") or part in _SKIP_DIRS for part in rel_parts[:-1]):
            continue
        out.append(p)
    return out


def _iter_attachments(folder: pathlib.Path) -> list[pathlib.Path]:
    out = []
    for p in sorted(folder.rglob("*")):
        if not p.is_file() or p.suffix.lower() == ".md":
            continue
        rel_parts = p.relative_to(folder).parts
        if any(part.startswith(".") or part in _SKIP_DIRS for part in rel_parts):
            continue
        out.append(p)
    return out


def _is_daily_dir(folder: pathlib.Path, md_files: list[pathlib.Path]) -> bool:
    if _DAILY_NAME_RE.search(folder.name):
        return True
    if not md_files:
        return False
    dated = sum(1 for p in md_files if _DATE_STEM_RE.match(p.stem))
    return dated / len(md_files) >= 0.8


def _next_unfiled_start(inbox: pathlib.Path) -> int:
    """Smallest unused UNFILED number, matching capture_writer's rule."""
    used: set[int] = set()
    pat = re.compile(r"UNFILED-(\d{3})\.md$", re.IGNORECASE)
    if inbox.is_dir():
        for entry in inbox.glob("UNFILED-*.md"):
            m = pat.search(entry.name)
            if m:
                used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return n


def build_plan(
    source: pathlib.Path,
    vault_path: pathlib.Path,
    dest_bucket: str = _PARKING_BUCKET,
) -> dict:
    """Scan `source` (read-only) and return a migration plan dict."""
    source = pathlib.Path(source).expanduser().resolve()
    vault_path = pathlib.Path(vault_path).expanduser().resolve()

    if not source.is_dir():
        raise MigrationError("SOURCE_INVALID", f"source is not a directory: {source}")
    if source == vault_path:
        raise MigrationError("SOURCE_INVALID", "source and target vault are the same path")
    if (source / _ACTIVE_BUCKET).is_dir():
        raise MigrationError(
            "SOURCE_INVALID",
            f"{source} already contains {_ACTIVE_BUCKET}/ — it looks like a squirrel vault.",
        )
    if dest_bucket not in (_ACTIVE_BUCKET, _PARKING_BUCKET):
        raise MigrationError("SOURCE_INVALID", f"invalid destination bucket: {dest_bucket}")

    today = _dt.date.today().isoformat()
    projects: list[dict] = []
    captures: list[dict] = []
    daily: list[dict] = []
    attachments: list[dict] = []
    skipped: list[dict] = []
    seen_tags: set[str] = set()

    unfiled_n = _next_unfiled_start(vault_path / "99-Resources" / "Inbox")

    for entry in sorted(source.iterdir(), key=lambda p: p.name.lower()):
        if entry.name.startswith(".") or entry.name in _SKIP_DIRS:
            continue

        if entry.is_file():
            if entry.suffix.lower() == ".md":
                target = vault_path / "99-Resources" / "Inbox" / f"UNFILED-{unfiled_n:03d}.md"
                captures.append({"source": str(entry), "target": str(target)})
                unfiled_n += 1
            else:
                attachments.append({
                    "source": str(entry),
                    "target": str(vault_path / "99-Resources" / "Obsidian-Attachments" / entry.name),
                })
            continue

        md_files = _iter_md_files(entry)
        for att in _iter_attachments(entry):
            attachments.append({
                "source": str(att),
                "target": str(
                    vault_path / "99-Resources" / "Obsidian-Attachments"
                    / att.relative_to(source)
                ),
            })
        if not md_files:
            skipped.append({"source": str(entry), "reason": "no markdown notes"})
            continue

        if _is_daily_dir(entry, md_files):
            for p in md_files:
                daily.append({"source": str(p), "target": str(vault_path / "04-Daily" / p.name)})
            continue

        tag = _sanitize_tag(entry.name)
        if tag is None:
            skipped.append({"source": str(entry), "reason": "folder name yields no valid project tag"})
            continue
        base, n = tag, 2
        while tag in seen_tags:
            tag, n = f"{base}-{n}", n + 1
        seen_tags.add(tag)

        project_dir = vault_path / dest_bucket / tag
        folder_note = next(
            (p for p in md_files if p.parent == entry and p.stem.lower() == entry.name.lower()),
            None,
        )
        intents = []
        nnn = 1
        for p in md_files:
            if p == folder_note:
                continue
            intents.append({
                "source": str(p),
                "target": str(project_dir / f"{tag}-NOTE-{nnn:03d}.md"),
                "id": f"{tag}-NOTE-{nnn:03d}",
            })
            nnn += 1
        projects.append({
            "tag": tag,
            "source_dir": str(entry),
            "page": {
                "target": str(project_dir / f"{tag}.md"),
                "from_note": str(folder_note) if folder_note else None,
            },
            "intents": intents,
        })

    if not (projects or captures or daily or attachments):
        raise MigrationError("NOTHING_TO_MIGRATE", f"nothing to migrate in {source}")

    return {
        "schema": 1,
        "created": today,
        "source": str(source),
        "vault": str(vault_path),
        "dest_bucket": dest_bucket,
        "projects": projects,
        "captures": captures,
        "daily": daily,
        "attachments": attachments,
        "skipped": skipped,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────

def _fm_value(val) -> str:
    if isinstance(val, list):
        return "[" + ", ".join(str(v) for v in val) + "]"
    return str(val)


def _render_frontmatter(owned: list[tuple[str, object]], extra: dict) -> str:
    lines = ["---"]
    for key, val in owned:
        lines.append(f"{key}: {_fm_value(val)}")
    for key, val in extra.items():
        if key not in _OWNED_KEYS:
            lines.append(f"{key}: {_fm_value(val)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _ensure_h1(body: str, fallback_title: str) -> str:
    if _H1_RE.search(body):
        return body
    return f"\n# {fallback_title}\n{body}"


def _render_intent(source: pathlib.Path, plan_source_root: pathlib.Path,
                   intent_id: str, tag: str) -> str:
    fm, body = parse_frontmatter(source.read_text(encoding="utf-8"))
    status = _map_status(fm.get("status"))
    tags = [t for t in (fm.get("tags") or []) if isinstance(t, str)]
    for t in ("intent", f"project/{tag}", "migrated/obsidian"):
        if t not in tags:
            tags.append(t)
    owned = [
        ("id", intent_id),
        ("project", tag),
        ("status", status),
        ("created", _note_created(fm, source)),
        ("tags", tags),
        ("migrated_from", str(source.relative_to(plan_source_root))),
    ]
    return _render_frontmatter(owned, fm) + _ensure_h1(body, source.stem)


def _render_capture(source: pathlib.Path, plan_source_root: pathlib.Path,
                    note_id: str) -> str:
    fm, body = parse_frontmatter(source.read_text(encoding="utf-8"))
    tags = [t for t in (fm.get("tags") or []) if isinstance(t, str)]
    for t in ("capture", "project/unfiled", "migrated/obsidian"):
        if t not in tags:
            tags.append(t)
    owned = [
        ("id", note_id),
        ("project", "unfiled"),
        ("type", "capture"),
        ("status", "pending"),
        ("created", _note_created(fm, source)),
        ("tags", tags),
        ("migrated_from", str(source.relative_to(plan_source_root))),
    ]
    return _render_frontmatter(owned, fm) + _ensure_h1(body, source.stem)


def _render_project_page(project: dict, plan_source_root: pathlib.Path) -> str:
    tag = project["tag"]
    source_dir = pathlib.Path(project["source_dir"])
    from_note = project["page"]["from_note"]
    if from_note:
        note = pathlib.Path(from_note)
        fm, body = parse_frontmatter(note.read_text(encoding="utf-8"))
        created = _note_created(fm, note)
        body = _ensure_h1(body, source_dir.name)
    else:
        fm = {}
        created = _dt.date.fromtimestamp(source_dir.stat().st_mtime).isoformat()
        body = _PROJECT_PAGE_BODY.format(
            name=source_dir.name,
            source_dir=str(source_dir.relative_to(plan_source_root)),
        )
    tags = [t for t in (fm.get("tags") or []) if isinstance(t, str)]
    for t in ("project", "type/C", "migrated/obsidian"):
        if t not in tags:
            tags.append(t)
    owned = [
        ("id", tag),
        ("type", "C"),
        ("status", "wip"),
        ("created", created),
        ("tags", tags),
        ("migrated_from", str(source_dir.relative_to(plan_source_root))),
    ]
    return _render_frontmatter(owned, fm) + body


# ─────────────────────────────────────────────────────────────────────────────
# Apply
# ─────────────────────────────────────────────────────────────────────────────

def _write_new(target: pathlib.Path, content: str, summary: dict) -> None:
    if target.exists():
        summary["skipped_existing"].append(str(target))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(target)
    summary["written"].append(str(target))


def _copy_new(source: pathlib.Path, target: pathlib.Path, summary: dict) -> None:
    if target.exists():
        summary["skipped_existing"].append(str(target))
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    summary["written"].append(str(target))


def apply_plan(plan: dict) -> dict:
    """Execute a plan produced by build_plan. Returns a summary dict."""
    if not isinstance(plan, dict) or plan.get("schema") != 1:
        raise MigrationError("PLAN_INVALID", "plan is missing or has an unknown schema")
    source_root = pathlib.Path(plan["source"])
    if not source_root.is_dir():
        raise MigrationError("SOURCE_INVALID", f"source vanished: {source_root}")

    summary: dict = {"written": [], "skipped_existing": [], "missing_source": []}

    for project in plan.get("projects", []):
        _write_new(
            pathlib.Path(project["page"]["target"]),
            _render_project_page(project, source_root),
            summary,
        )
        for intent in project["intents"]:
            src = pathlib.Path(intent["source"])
            if not src.is_file():
                summary["missing_source"].append(str(src))
                continue
            _write_new(
                pathlib.Path(intent["target"]),
                _render_intent(src, source_root, intent["id"], project["tag"]),
                summary,
            )

    for cap in plan.get("captures", []):
        src = pathlib.Path(cap["source"])
        if not src.is_file():
            summary["missing_source"].append(str(src))
            continue
        target = pathlib.Path(cap["target"])
        _write_new(target, _render_capture(src, source_root, target.stem), summary)

    for entry in plan.get("daily", []) + plan.get("attachments", []):
        src = pathlib.Path(entry["source"])
        if not src.is_file():
            summary["missing_source"].append(str(src))
            continue
        _copy_new(src, pathlib.Path(entry["target"]), summary)

    summary["written_count"] = len(summary["written"])
    summary["skipped_count"] = len(summary["skipped_existing"])
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Human-readable plan + CLI
# ─────────────────────────────────────────────────────────────────────────────

def format_plan(plan: dict) -> str:
    lines = [
        f"Migration plan — {plan['source']}",
        f"  → vault: {plan['vault']}  (projects land in {plan['dest_bucket']}/)",
        "",
    ]
    for p in plan["projects"]:
        page_src = "folder note" if p["page"]["from_note"] else "generated"
        lines.append(f"  📁 {pathlib.Path(p['source_dir']).name}  →  {p['tag']}  "
                     f"(page: {page_src}, {len(p['intents'])} intents)")
    if plan["captures"]:
        lines.append(f"  📥 {len(plan['captures'])} loose note(s) → 99-Resources/Inbox/ (captures)")
    if plan["daily"]:
        lines.append(f"  📅 {len(plan['daily'])} daily note(s) → 04-Daily/")
    if plan["attachments"]:
        lines.append(f"  📎 {len(plan['attachments'])} attachment(s) → 99-Resources/Obsidian-Attachments/")
    for s in plan["skipped"]:
        lines.append(f"  ⏭  skipped {s['source']} — {s['reason']}")
    lines.append("")
    lines.append("Source vault is read-only: nothing is modified until `apply`.")
    return "\n".join(lines)


def _resolve_vault(name: Optional[str]) -> pathlib.Path:
    from config_loader import ConfigError, VaultNotFoundError, get_vault
    try:
        vault = get_vault(name=name)
    except VaultNotFoundError as e:
        raise MigrationError("VAULT_UNKNOWN", str(e))
    except ConfigError as e:
        raise MigrationError("NO_CONFIG", str(e))
    path = pathlib.Path(vault.path).expanduser().resolve()
    if not path.exists():
        raise MigrationError("VAULT_MISSING", f"vault path on disk is missing: {path}")
    return path


def main() -> int:
    p = argparse.ArgumentParser(prog="vault_migrator")
    sub = p.add_subparsers(dest="cmd", required=True)

    plan_p = sub.add_parser("plan", help="scan source vault, write migration plan")
    plan_p.add_argument("--source", required=True)
    plan_p.add_argument("--vault", default=None, help="target vault name (default vault if omitted)")
    plan_p.add_argument("--dest", choices=["parking", "active"], default="parking")
    plan_p.add_argument("--out", default=str(pathlib.Path.home() / ".squirrel" / "migration-plan.json"))
    plan_p.add_argument("--json", action="store_true", help="print plan JSON instead of summary")

    apply_p = sub.add_parser("apply", help="execute a saved migration plan")
    apply_p.add_argument("--plan", default=str(pathlib.Path.home() / ".squirrel" / "migration-plan.json"))
    apply_p.add_argument("--json", action="store_true", help="print summary as JSON")

    args = p.parse_args()
    try:
        if args.cmd == "plan":
            vault_path = _resolve_vault(args.vault)
            bucket = _ACTIVE_BUCKET if args.dest == "active" else _PARKING_BUCKET
            plan = build_plan(pathlib.Path(args.source), vault_path, bucket)
            out = pathlib.Path(args.out).expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(plan, indent=2), encoding="utf-8")
            if args.json:
                print(json.dumps(plan, indent=2))
            else:
                print(format_plan(plan))
                print(f"\nPlan saved: {out}")
                print("Review it, then run:  vault_migrator apply")
        else:
            plan_file = pathlib.Path(args.plan).expanduser()
            if not plan_file.is_file():
                raise MigrationError("PLAN_INVALID", f"plan file not found: {plan_file}")
            try:
                plan = json.loads(plan_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise MigrationError("PLAN_INVALID", f"plan file is not valid JSON: {e}")
            summary = apply_plan(plan)
            if args.json:
                print(json.dumps(summary, indent=2))
            else:
                print(f"✅ Migration applied: {summary['written_count']} file(s) written, "
                      f"{summary['skipped_count']} skipped (already exist).")
                for miss in summary["missing_source"]:
                    print(f"  ⚠️ source note vanished, skipped: {miss}")
    except MigrationError as e:
        print(f"{e.code}: {e.message}", file=sys.stderr)
        return _CODE_TO_EXIT.get(e.code, 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
