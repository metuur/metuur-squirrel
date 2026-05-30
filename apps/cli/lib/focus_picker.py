#!/usr/bin/env python3
"""
focus_picker.py — Manual focus pick (Today / Week) read & write helpers.

Stores the user's manual focus as a single frontmatter key on the chosen intent
file (`focus_today` or `focus_week`). Expiry is read-time only: a YAML value
that does not match the current token is treated as unset. The single-pick
invariant (R-2.1 / R-2.2) is enforced by a strip-before-write pass that scans
intent files under `01-Proyectos-Activos/*/` and removes any entry whose value
equals the CURRENT token (stale entries are left alone — R-2.5).

Public API:
    _token_now(slot, now=None) -> str
    get_manual_focus(vault, now=None) -> dict
    set_manual_focus(vault, slot, project_slug, intent_slug, now=None) -> None
    clear_manual_focus(vault, slot, now=None) -> None

`slot` is always one of "today" or "week".

Time semantics (R-1.3): "now" defaults to the host's local wall clock
(`datetime.datetime.now()`); tests inject a frozen `datetime.datetime` via the
`now=` argument. There is no real timezone argument — local-tz semantics come
from using local-wall-clock by default.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import Optional

# @spec R-1.1, R-1.2, R-1.3, R-1.4, R-1.5, R-1.8, R-2.1, R-2.2, R-2.3, R-2.4, R-2.5, R-2.6, R-9.3, R-9.4

# Import siblings.
sys.path.insert(0, str(Path(__file__).parent))
from intent_parser import _DELETE, parse_intent, write_frontmatter  # noqa: E402
from status_aggregator import find_intents_for_project, find_projects  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Errors
# ─────────────────────────────────────────────────────────────────────────────

class IntentNotFound(Exception):
    """Raised when set_manual_focus is asked to target a non-existent intent."""

    def __init__(self, project_slug: str, intent_slug: str):
        super().__init__(f"intent not found: {project_slug}/{intent_slug}")
        self.project_slug = project_slug
        self.intent_slug = intent_slug


# ─────────────────────────────────────────────────────────────────────────────
# Token computation
# ─────────────────────────────────────────────────────────────────────────────

def _token_now(slot: str, now: Optional[datetime.datetime] = None) -> str:
    """Return the current token string for `slot`.

    - slot="today"    -> "YYYY-MM-DD"    (local date).
    - slot="today_pm" -> "YYYY-MM-DD-PM" (local date with PM suffix).
    - slot="week"     -> "GGGG-Www"      (ISO-8601 year-week, e.g. "2026-W22").
    - Raises ValueError on any other slot.

    If `now` is None, the host's local wall clock is used (R-1.3).
    """
    if slot not in ("today", "today_pm", "week"):
        raise ValueError(f"unknown slot: {slot!r} (expected 'today', 'today_pm', or 'week')")

    n = now if now is not None else datetime.datetime.now()
    if slot == "today":
        return n.strftime("%Y-%m-%d")
    if slot == "today_pm":
        return n.strftime("%Y-%m-%d-PM")
    return n.strftime("%G-W%V")


def _slot_key(slot: str) -> str:
    """Frontmatter key for a slot."""
    if slot == "today":
        return "focus_today"
    if slot == "today_pm":
        return "focus_today_pm"
    if slot == "week":
        return "focus_week"
    raise ValueError(f"unknown slot: {slot!r}")


# ─────────────────────────────────────────────────────────────────────────────
# Vault traversal
# ─────────────────────────────────────────────────────────────────────────────

def _iter_intent_paths(vault: Path):
    """Yield every intent .md path under 01-Proyectos-Activos/*/."""
    projects = find_projects(vault).get("wip", [])
    for project_md in projects:
        for intent_md in find_intents_for_project(project_md):
            yield project_md, intent_md


# ─────────────────────────────────────────────────────────────────────────────
# Read
# ─────────────────────────────────────────────────────────────────────────────

def get_manual_focus(vault: Path, now: Optional[datetime.datetime] = None) -> dict:
    """Return `{"today": ManualPick|None, "week": ManualPick|None}`.

    A slot is populated iff some intent file's `focus_today` / `focus_week`
    frontmatter value equals the current local token (R-1.4 / R-1.5). If more
    than one intent carries the current token (manual Obsidian dup), the one
    with the most recent file mtime wins (R-2.6) — no error is raised.
    """
    today_token = _token_now("today", now=now)
    week_token = _token_now("week", now=now)

    candidates: dict[str, list[tuple[Path, Path, dict]]] = {"today": [], "week": []}

    for project_md, intent_path in _iter_intent_paths(vault):
        try:
            intent = parse_intent(intent_path)
        except Exception:
            continue
        fm = intent.get("frontmatter", {}) or {}
        if fm.get("focus_today") == today_token:
            candidates["today"].append((project_md, intent_path, intent))
        if fm.get("focus_week") == week_token:
            candidates["week"].append((project_md, intent_path, intent))

    result: dict = {"today": None, "week": None}
    for slot, items in candidates.items():
        if not items:
            continue
        # R-2.6 tiebreak: most recent mtime wins.
        items.sort(key=lambda t: t[1].stat().st_mtime, reverse=True)
        project_md, intent_path, intent = items[0]
        result[slot] = _build_pick(project_md, intent_path, intent, slot)

    return result


def _build_pick(
    project_md: Path,
    intent_path: Path,
    intent: dict,
    slot: str,
) -> dict:
    """Assemble the ManualPick dict for a winning intent."""
    project_slug = project_md.parent.name
    project_title = project_slug
    try:
        page = parse_intent(project_md)
        title = page.get("title") or ""
        if title:
            project_title = title
    except Exception:
        pass

    fm = intent.get("frontmatter", {}) or {}
    notes = intent.get("shutdown_notes") or []
    next_action = None
    if notes:
        next_action = notes[0].get("next_action")

    key = _slot_key(slot)
    return {
        "project_slug": project_slug,
        "project_title": project_title,
        "intent_slug": intent_path.stem,
        "intent_title": intent.get("title") or intent_path.stem,
        "next_action": next_action,
        "picked_on": fm.get(key, ""),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Write
# ─────────────────────────────────────────────────────────────────────────────

def set_manual_focus(
    vault: Path,
    slot: str,
    project_slug: str,
    intent_slug: str,
    now: Optional[datetime.datetime] = None,
) -> None:
    """Pin a single intent as the manual focus for `slot`.

    Steps:
      1. Resolve target intent file; raise IntentNotFound if missing.
      2. Compute the current token; pick the matching frontmatter key.
      3. Strip pass (R-2.1, R-2.2, R-2.5): scan every intent and remove the
         key wherever its value equals the CURRENT token. Stale tokens are
         left alone. This includes the target file — the subsequent upsert
         puts the key back (R-2.4 idempotent set).
      4. Write pass: upsert `key: token` on the target file.

    R-2.3: the OTHER slot's key is never touched.
    R-1.8: all I/O stays inside `vault`.
    """
    target = vault / "01-Proyectos-Activos" / project_slug / f"{intent_slug}.md"
    if not target.is_file():
        raise IntentNotFound(project_slug, intent_slug)

    key = _slot_key(slot)
    token = _token_now(slot, now=now)

    # Strip pass — bounded to the current token (R-2.5).
    for _project_md, intent_path in _iter_intent_paths(vault):
        try:
            intent = parse_intent(intent_path)
        except Exception:
            continue
        fm = intent.get("frontmatter", {}) or {}
        if fm.get(key) == token:
            write_frontmatter(intent_path, {key: _DELETE})

    # Write pass — idempotent upsert (R-2.4).
    write_frontmatter(target, {key: token})


def clear_manual_focus(
    vault: Path,
    slot: str,
    now: Optional[datetime.datetime] = None,
) -> None:
    """Remove `slot`'s key from every intent carrying it with the CURRENT token.

    Mirrors the strip pass of set_manual_focus without a follow-up write
    (R-3.5 semantics, scoped to the cli helper layer).
    """
    key = _slot_key(slot)
    token = _token_now(slot, now=now)

    for _project_md, intent_path in _iter_intent_paths(vault):
        try:
            intent = parse_intent(intent_path)
        except Exception:
            continue
        fm = intent.get("frontmatter", {}) or {}
        if fm.get(key) == token:
            write_frontmatter(intent_path, {key: _DELETE})
