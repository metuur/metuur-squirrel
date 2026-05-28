#!/usr/bin/env python3
"""
lib/capture_writer.py — write a capture file from free-text input.

Shared helper for the web UI capture flow and any future caller. Picks the
right folder + filename per the existing intent_parser numbering rules and
writes atomically.

Public API:

    write_capture(
        vault_path: pathlib.Path,
        project_slug: str | None,
        text: str,
    ) -> pathlib.Path

Spec source: docs/ears/web-ui-simple.md (R-5.4, R-5.5, R-5.6)
"""

from __future__ import annotations

import datetime
import os
import pathlib
import re
from typing import Optional


def write_capture(
    vault_path: pathlib.Path,
    project_slug: Optional[str],
    text: str,
) -> pathlib.Path:
    """Write a capture note and return its path.

    With `project_slug`: file lives in `<vault>/01-Proyectos-Activos/<slug>/`
    with the name `<slug>-CAPTURE-<NNN>.md` (R-5.5).

    Without `project_slug`: file lives in `<vault>/99-Resources/Inbox/` with
    the name `UNFILED-<NNN>.md` (R-5.4).

    Numbering: zero-padded 3-digit; the next number is the smallest integer
    not already used in the target folder.

    Write is atomic: temp file in the target folder + `os.replace`.
    """
    if not text or not text.strip():
        raise ValueError("capture text must be non-empty")
    vault_path = pathlib.Path(vault_path).expanduser().resolve()

    if project_slug:
        folder = vault_path / "01-Proyectos-Activos" / project_slug
        prefix = f"{project_slug}-CAPTURE"
        tipo = "capture"
        meta_proj = project_slug
    else:
        folder = vault_path / "99-Resources" / "Inbox"
        prefix = "UNFILED"
        tipo = "capture"
        meta_proj = "unfiled"

    folder.mkdir(parents=True, exist_ok=True)

    nnn = _next_number(folder, prefix)
    name = f"{prefix}-{nnn:03d}.md"
    target = folder / name

    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    iso = now.replace(microsecond=0).isoformat()

    body = _format_note(
        note_id=target.stem,
        project=meta_proj,
        tipo=tipo,
        created_iso=iso,
        text=text.strip(),
    )

    _atomic_write(target, body)
    return target


def _next_number(folder: pathlib.Path, prefix: str) -> int:
    """Return the next integer N such that `<prefix>-<NNN>.md` is unused."""
    used: set[int] = set()
    pat = re.compile(re.escape(prefix) + r"-(\d{3})\.md$", re.IGNORECASE)
    for entry in folder.glob(f"{prefix}-*.md"):
        m = pat.search(entry.name)
        if m:
            used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return n


def _format_note(
    *,
    note_id: str,
    project: str,
    tipo: str,
    created_iso: str,
    text: str,
) -> str:
    return (
        "---\n"
        f"id: {note_id}\n"
        f"proyecto: {project}\n"
        f"tipo: {tipo}\n"
        "estado: pending\n"
        f"creado: {created_iso}\n"
        f"tags: [capture, proyecto/{project}]\n"
        "---\n\n"
        f"# {note_id}\n\n"
        f"{text}\n"
    )


def _atomic_write(target: pathlib.Path, body: str) -> None:
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, target)
