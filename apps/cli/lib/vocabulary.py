#!/usr/bin/env python3
"""
lib/vocabulary.py — translate internal Squirrel terms to user-facing labels.

One-way: internal → user-facing. Used by the web UI to keep developer
vocabulary out of HTML rendered for non-technical users (R-4.1–R-4.7).

Public API:

    translate(internal: str, *, multi_vault: bool = False) -> str | None
    project_title(slug: str, vault_path: pathlib.Path | None = None) -> str
    urgency_label(level: str) -> str
    FORBIDDEN_IN_USER_HTML: frozenset[str]

Spec source: docs/ears/web-ui-simple.md (unit 4)
"""

from __future__ import annotations

import pathlib
import re
from typing import Optional

# ─── Internal → user-facing mappings ─────────────────────────────────────────
#
# Keys are the internal Squirrel terms. Values are the user-facing labels.
# A None value means "never render this in user-visible HTML" (admin-only).

_BASE_TERMS: dict[str, Optional[str]] = {
    # PARA folder names → friendly section titles
    "01-Proyectos-Activos": "My projects",
    "02-Areas": "Areas",                 # admin only
    "03-Recursos": "Reference",          # admin only
    "04-Archivo": "Archive",             # admin only
    "02-Parking-Lot": "On hold",
    "99-Resources": None,                # never user-visible

    # Note types
    "intent": "note",
    "capture": "note",
    "decision": "important note",
    "shutdown note": "session summary",

    # Frontmatter concepts (never user-visible)
    "frontmatter": None,
    "type": None,
    "status": None,
    "project": None,
    "wiki-link": None,
    "PARA": None,
    ".md": None,
    "parakeet": None,

    # Tags
    "tag": "topic",
    "tags": "topics",
}


# Urgency → friendly grouping (R-4.6)
_URGENCY: dict[str, str] = {
    "overdue": "Today / Overdue",
    "critical": "Today / Tomorrow",
    "urgent": "Today / Tomorrow",
    "soon": "This week",
    "upcoming": "Later",
    "eventual": "Later",
    "distant": "Later",
    "future_fyi": "Later",
}


# Forbidden terms that must NEVER appear in user-facing HTML (R-4.4).
# `vault` is conditional — allowed only when multiple vaults are configured
# (where it becomes `workspace`). It is added/removed dynamically by
# forbidden_terms().
FORBIDDEN_IN_USER_HTML: frozenset[str] = frozenset(
    {
        "frontmatter",
        "PARA",
        "intent",
        "wiki-link",
        ".md",
        "project",
        "type",
        "status",
        "01-Proyectos-Activos",
        "02-Areas",
        "03-Recursos",
        "04-Archivo",
        "02-Parking-Lot",
        "99-Resources",
        "shutdown note",
        "parakeet",
    }
)


def forbidden_terms(*, multi_vault: bool) -> frozenset[str]:
    """Return forbidden terms for the active config.

    Single-vault: `vault` is forbidden (R-4.2).
    Multi-vault: `vault` is allowed (R-4.3, but `workspace` is preferred).
    """
    if multi_vault:
        return FORBIDDEN_IN_USER_HTML
    return FORBIDDEN_IN_USER_HTML | {"vault"}


def translate(internal: str, *, multi_vault: bool = False) -> Optional[str]:
    """Translate a single internal term to its user-facing label.

    Returns the user-facing string, or None when the term must never be
    shown to users (admin-only term). Unknown terms pass through unchanged
    (caller's responsibility).
    """
    if internal in _BASE_TERMS:
        return _BASE_TERMS[internal]
    # The `vault` term flips on multi_vault.
    if internal == "vault":
        return "workspace" if multi_vault else None
    return internal


def urgency_label(level: str) -> str:
    """Return the user-facing label for a deadline urgency level (R-4.6).

    Unknown levels fall back to "Later" so the UI never renders raw
    developer vocabulary.
    """
    return _URGENCY.get(level.lower(), "Later")


def workspace_word(*, multi_vault: bool) -> Optional[str]:
    """Return the right word for "vault" given the active config.

    Single-vault: None (the concept is hidden entirely — R-4.2).
    Multi-vault: "workspace" (R-4.3).
    """
    return "workspace" if multi_vault else None


def project_title(slug: str, vault_path: Optional[pathlib.Path] = None) -> str:
    """Return the user-facing human title for a project slug (R-4.5).

    Looks for `<vault>/01-Proyectos-Activos/<slug>/<slug>.md` and reads the
    first `# Heading` line. Falls back to a Capitalized form of the slug if
    no title is found or vault_path was not provided.
    """
    if vault_path is not None:
        candidate = (
            pathlib.Path(vault_path)
            / "01-Proyectos-Activos"
            / slug
            / f"{slug}.md"
        )
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8", errors="replace")
            # Skip frontmatter block to find the first body-level `# Heading`
            in_fm = False
            for i, line in enumerate(text.splitlines()):
                stripped = line.rstrip()
                if i == 0 and stripped == "---":
                    in_fm = True
                    continue
                if in_fm and stripped == "---":
                    in_fm = False
                    continue
                if in_fm:
                    continue
                m = re.match(r"^#\s+(.+?)\s*$", stripped)
                if m:
                    return m.group(1)
    return _humanize_slug(slug)


def _humanize_slug(slug: str) -> str:
    """`PROYECTO-A-AUTH` -> `Proyecto A Auth` (fallback only)."""
    parts = re.split(r"[-_]+", slug)
    return " ".join(p.capitalize() if p else p for p in parts if p) or slug


if __name__ == "__main__":
    # Quick smoke test
    import sys
    for term in sys.argv[1:]:
        out = translate(term)
        print(f"{term!r} -> {out!r}")
