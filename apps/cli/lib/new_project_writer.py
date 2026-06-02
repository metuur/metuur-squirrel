#!/usr/bin/env python3
"""new_project_writer.py — Scaffold a new project in the vault.

Public API (callable from server.py and the CLI):

    create_project(
        tag: str,
        tipo: str,
        vault_name: str | None = None,
        deadline: str | None = None,
        stakeholders: str | None = None,
        description: str = "",
        first_intent_tag: str | None = None,
        first_intent_title: str = "",
        force: bool = False,
    ) -> dict

Raises NewProjectError(code, message). The `code` matches the CLI exit-code
sentinels so the skill and the web server can share one error vocabulary.

Creates:
  <vault>/01-Proyectos-Activos/<TAG>/<TAG>.md           (project page)
  <vault>/01-Proyectos-Activos/<TAG>/<FIRST-INTENT>.md  (optional)

Refuses to overwrite. Refuses to exceed the WIP cap unless `force=True`.

CLI exit codes:
  0  success
  2  NO_CONFIG       no config / no default vault
  3  VAULT_MISSING   vault path on disk is missing
  4  VAULT_UNKNOWN   named vault not found
  5  INVALID_TAG     invalid project tag
  6  PROJECT_EXISTS  project already exists
  7  WIP_CAPACITY    WIP at capacity (use --force to override)
  8  VALIDATION      tipo / deadline / first intent invalid
"""
from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import re
import sys
from typing import Optional

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config_loader import ConfigError, VaultNotFoundError, get_vault  # noqa: E402
from status_aggregator import aggregate_status  # noqa: E402
from tag_parser import validate as validate_intent_tag  # noqa: E402

# Project tag: 1+ uppercase-alphanumeric segments separated by dashes.
# First segment must start with a letter; later segments may be all digits.
# Examples: DEMO, VISA-FAMILIA, CASA-CONTABILIDAD-TAXES-2025
_PROJECT_TAG_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$")

_VALID_TIPOS = {"A", "B", "C"}

_CODE_TO_EXIT = {
    "NO_CONFIG":     2,
    "VAULT_MISSING": 3,
    "VAULT_UNKNOWN": 4,
    "INVALID_TAG":   5,
    "PROJECT_EXISTS": 6,
    "WIP_CAPACITY":  7,
    "INVALID_TIPO":  8,
    "INVALID_DEADLINE": 8,
    "INVALID_INTENT_TAG": 8,
    "INTENT_TAG_MISMATCH": 8,
    "INVALID_INTENT_FILENAME": 8,
}

_PROJECT_PAGE_TEMPLATE = """---
id: {tag}
type: {tipo}
status: wip
created: {creado}
{deadline_line}{stakeholders_line}tags: [project, project/active, type/{tipo}]
---

# {tag}

{description}

## 🎯 Objective
<What you want to achieve with this project and why it matters.>

## ✅ Definition of Done
- [ ] <Concrete, verifiable criterion>
- [ ] <Concrete, verifiable criterion>

## 🧩 Intents
<!-- Intents live as sibling files `<TAG>-<SUBAREA>-NNN.md` -->

## 📝 Context
<Background info, links, decisions made outside an ADR>
"""


class NewProjectError(Exception):
    """Raised when create_project cannot proceed. Carries a stable error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _resolve_vault(name: Optional[str]) -> pathlib.Path:
    try:
        vault = get_vault(name=name)
    except VaultNotFoundError as e:
        raise NewProjectError("VAULT_UNKNOWN", str(e))
    except ConfigError as e:
        raise NewProjectError("NO_CONFIG", str(e))
    path = pathlib.Path(vault.path).expanduser().resolve()
    if not path.exists():
        raise NewProjectError("VAULT_MISSING", f"vault path on disk is missing: {path}")
    return path


def _validate_project_tag(tag: str) -> None:
    if not _PROJECT_TAG_RE.match(tag):
        raise NewProjectError(
            "INVALID_TAG",
            f"{tag!r} is not a valid project tag. Expected UPPERCASE letters/digits "
            f"with dashes (e.g. MYAPP or VISA-FAMILIA).",
        )
    parts = tag.split("-")
    if len(parts) == 4 and parts[-1].isdigit() and len(parts[-1]) == 3:
        raise NewProjectError(
            "INVALID_TAG",
            f"{tag!r} looks like an intent tag (4 parts ending in NNN). "
            f"Project tags should not match the intent schema.",
        )


def _validate_tipo(tipo: str) -> None:
    if tipo not in _VALID_TIPOS:
        raise NewProjectError(
            "INVALID_TIPO",
            f"{tipo!r} — must be one of {sorted(_VALID_TIPOS)} "
            f"(A=mission-critical, B=important, C=experimental).",
        )


def _validate_deadline(deadline: Optional[str]) -> Optional[str]:
    if deadline is None or deadline == "":
        return None
    try:
        _dt.date.fromisoformat(deadline)
    except ValueError:
        raise NewProjectError(
            "INVALID_DEADLINE",
            f"{deadline!r} — must be ISO date YYYY-MM-DD.",
        )
    return deadline


def _validate_first_intent(project_tag: str, intent_tag: Optional[str]) -> None:
    if intent_tag is None or intent_tag == "":
        return
    ok, suggestion = validate_intent_tag(intent_tag)
    if not ok:
        hint = f" Suggestion: {suggestion}." if suggestion else ""
        raise NewProjectError(
            "INVALID_INTENT_TAG",
            f"{intent_tag!r} is not a valid intent tag "
            f"(expected PROJECT-SUBAREA-COMPONENT-NNN).{hint}",
        )
    if not intent_tag.startswith(project_tag + "-"):
        raise NewProjectError(
            "INTENT_TAG_MISMATCH",
            f"{intent_tag!r} must start with {project_tag!r}-",
        )


_INTENT_FILENAME_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$")


def _validate_first_intent_filename(filename: Optional[str]) -> None:
    if not filename:
        return
    if not _INTENT_FILENAME_RE.match(filename):
        raise NewProjectError(
            "INVALID_INTENT_FILENAME",
            f"{filename!r} is not a valid intent filename. Expected UPPERCASE letters/digits with dashes.",
        )


def _check_wip_capacity(vault_path: pathlib.Path, force: bool) -> tuple[int, int]:
    agg = aggregate_status(vault_path)
    wip = agg.get("wip") or {}
    count = int(wip.get("count") or 0)
    cap = int(wip.get("max") or 3)
    if count >= cap and not force:
        raise NewProjectError(
            "WIP_CAPACITY",
            f"vault is at {count}/{cap} WIP projects. "
            f"Pass force=True to add this project anyway, or park an existing one first.",
        )
    return count, cap


def _stakeholders_yaml(raw: Optional[str]) -> str:
    if not raw:
        return "stakeholders: []\n"
    items = [s.strip() for s in raw.split(",") if s.strip()]
    if not items:
        return "stakeholders: []\n"
    rendered = ", ".join(items)
    return f"stakeholders: [{rendered}]\n"


def _render_project_page(
    tag: str,
    tipo: str,
    creado: str,
    deadline: Optional[str],
    stakeholders: Optional[str],
    description: str,
) -> str:
    deadline_line = f"deadline: {deadline}\n" if deadline else ""
    stakeholders_line = _stakeholders_yaml(stakeholders)
    return _PROJECT_PAGE_TEMPLATE.format(
        tag=tag,
        tipo=tipo,
        creado=creado,
        deadline_line=deadline_line,
        stakeholders_line=stakeholders_line,
        description=description or f"Proyecto {tag}.",
    )


def _render_first_intent(
    intent_tag: str,
    project_tag: str,
    title: str,
    creado_iso: str,
) -> Optional[str]:
    template_path = _HERE.parent / "templates" / "intent.md"
    if not template_path.exists():
        return None
    text = template_path.read_text(encoding="utf-8")
    text = text.replace("<TAG>", intent_tag)
    text = text.replace("<PROJECT>", project_tag)
    text = text.replace("<YYYY-MM-DD>", creado_iso[:10])
    text = text.replace("<Título corto>", title or intent_tag)
    return text


def create_project(
    *,
    tag: str,
    tipo: str,
    vault_name: Optional[str] = None,
    deadline: Optional[str] = None,
    stakeholders: Optional[str] = None,
    description: str = "",
    first_intent_tag: Optional[str] = None,
    first_intent_title: str = "",
    first_intent_filename: Optional[str] = None,
    force: bool = False,
) -> dict:
    """Create a new project and return a summary dict.

    Raises NewProjectError on any failure.
    """
    tag = (tag or "").strip()
    _validate_project_tag(tag)
    _validate_tipo(tipo)
    deadline = _validate_deadline(deadline)
    _validate_first_intent(tag, first_intent_tag)
    _validate_first_intent_filename(first_intent_filename)

    vault_path = _resolve_vault(vault_name)

    project_dir = vault_path / "01-Proyectos-Activos" / tag
    project_page = project_dir / f"{tag}.md"
    if project_dir.exists() or project_page.exists():
        raise NewProjectError(
            "PROJECT_EXISTS",
            f"{project_dir} already exists. Refusing to overwrite.",
        )

    count, cap = _check_wip_capacity(vault_path, force)

    today_iso = _dt.date.today().isoformat()
    creado_iso = _dt.datetime.now().astimezone().isoformat(timespec="seconds")

    page_body = _render_project_page(
        tag=tag,
        tipo=tipo,
        creado=today_iso,
        deadline=deadline,
        stakeholders=stakeholders,
        description=(description or "").strip(),
    )

    intent_path: Optional[pathlib.Path] = None
    intent_body: Optional[str] = None
    if first_intent_tag:
        intent_body = _render_first_intent(
            intent_tag=first_intent_tag,
            project_tag=tag,
            title=first_intent_title,
            creado_iso=creado_iso,
        )
        if intent_body is not None:
            fname = (first_intent_filename or "").strip() or first_intent_tag
            intent_path = project_dir / f"{fname}.md"

    project_dir.mkdir(parents=True, exist_ok=False)
    project_page.write_text(page_body, encoding="utf-8")
    if intent_path is not None and intent_body is not None:
        intent_path.write_text(intent_body, encoding="utf-8")

    return {
        "tag": tag,
        "type": tipo,
        "deadline": deadline,
        "page_path": str(project_page),
        "intent_path": str(intent_path) if intent_path else None,
        "wip_count": count + 1,
        "wip_max": cap,
        "over_cap": (count + 1) > cap,
    }


def ensure_scratch_pad(vault_path: pathlib.Path) -> None:
    """Create SCRATCH-PAD project if absent. Called at every server start."""
    project_dir = vault_path / "01-Proyectos-Activos" / "SCRATCH-PAD"
    if project_dir.exists():
        return
    try:
        today_iso = _dt.date.today().isoformat()
        project_dir.mkdir(parents=True, exist_ok=True)
        page = project_dir / "SCRATCH-PAD.md"
        content = f"""---
id: SCRATCH-PAD
type: C
status: wip
created: {today_iso}
protected: true
tags: [project, project/active, type/C]
---

# SCRATCH-PAD

Default project for quick ideas, reminders, and captures.

## 🎯 Objective
Container for quick captures and scratch notes.

## ✅ Definition of Done
- [ ] Items moved to appropriate projects

## 🧩 Intents

## 📝 Context
"""
        page.write_text(content, encoding="utf-8")
    except Exception:
        pass  # Non-fatal: server starts anyway


def _print_summary(result: dict, first_intent_tag: Optional[str]) -> None:
    tag = result["tag"]
    print(f"✅ Created project: {tag}")
    print(f"   Page:    {result['page_path']}")
    if result.get("intent_path"):
        print(f"   Intent:  {result['intent_path']}")
    print(f"   Type:    {result['type']}")
    if result.get("deadline"):
        print(f"   Deadline: {result['deadline']}")
    over = "  ⚠️ over cap" if result.get("over_cap") else ""
    print(f"   WIP now: {result['wip_count']}/{result['wip_max']}{over}")
    print()
    print("Suggested next step:")
    if first_intent_tag:
        print(f"  /sq-start {tag}")
    else:
        print(f"  /sq-capture intent {tag}-... 'descripción del primer intent'")


def main() -> int:
    p = argparse.ArgumentParser(prog="new_project_writer")
    p.add_argument("--tag", required=True)
    p.add_argument("--type", dest="tipo", required=True, choices=sorted(_VALID_TIPOS))
    p.add_argument("--name", default=None)
    p.add_argument("--deadline", default=None)
    p.add_argument("--stakeholders", default=None)
    p.add_argument("--description", default="")
    p.add_argument("--first-intent-tag", default=None)
    p.add_argument("--first-intent-title", default="")
    p.add_argument("--first-intent-filename", default=None)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    try:
        result = create_project(
            tag=args.tag,
            tipo=args.tipo,
            vault_name=args.name,
            deadline=args.deadline,
            stakeholders=args.stakeholders,
            description=args.description,
            first_intent_tag=args.first_intent_tag,
            first_intent_title=args.first_intent_title,
            first_intent_filename=args.first_intent_filename,
            force=args.force,
        )
    except NewProjectError as e:
        print(f"{e.code}: {e.message}", file=sys.stderr)
        return _CODE_TO_EXIT.get(e.code, 1)

    _print_summary(result, args.first_intent_tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
