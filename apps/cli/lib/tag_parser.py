#!/usr/bin/env python3
"""
tag_parser.py — Sole authority for squirrel tag validation and normalisation.

Tag schema: PROYECTO-SUBÁREA-COMPONENTE-NNN
  - Exactly 4 dash-separated segments.
  - Segments 1-3: one or more uppercase ASCII letters/digits ([A-Z][A-Z0-9]*).
  - Segment 4: exactly 3 zero-padded digits (\\d{3}).
  - Full regex: ^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-\\d{3}$

VAULT-003 (R-1.3): no other module in lib/ or skills/ may contain a tag validation
regex. This file is the single source of truth.

Uso CLI:
    python3 tag_parser.py VISA-FAMILIA-TRAMITE-001  # exits 0 — valid
    python3 tag_parser.py VISA-001                  # exits 1 — invalid
"""

import re
import sys
from typing import Optional

# @spec VAULT-008
_TAG_RE = re.compile(r"^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-\d{3}$")
_SUFFIX_RE = re.compile(r"^(\d+)$")


# @spec VAULT-003
def validate(tag: Optional[str]) -> tuple[bool, Optional[str]]:
    """Return (True, None) if valid, (False, suggestion_or_None) if not.

    Suggestion is None when the tag is absent or structurally broken beyond
    fixable corrections (e.g. fewer than 3 named segments).
    """
    if not tag:
        return False, None

    if _TAG_RE.match(tag):
        return True, None

    suggestion = _suggest(tag)
    return False, suggestion


def normalize(tag: str) -> str:
    """Uppercase all segments and zero-pad the numeric suffix to 3 digits.

    Does not validate. Call validate() first if correctness matters.
    """
    parts = tag.upper().split("-")
    if len(parts) == 4 and parts[-1].isdigit():
        parts[-1] = parts[-1].zfill(3)
    return "-".join(parts)


# @spec VAULT-003
def parse(tag: str) -> Optional[dict]:
    """Return {"project", "subarea", "component", "number"} or None if not 4-part schema."""
    if not _TAG_RE.match(tag):
        return None
    p, s, c, n = tag.split("-")
    return {"project": p, "subarea": s, "component": c, "number": int(n)}


# ── internal ──────────────────────────────────────────────────────────────────

def _suggest(tag: str) -> Optional[str]:
    """Produce a corrected suggestion, or None if structurally unrecoverable."""
    # Step 1: uppercase + replace spaces/underscores
    candidate = tag.upper().replace(" ", "-").replace("_", "-")
    # Step 2: strip non-ASCII characters
    candidate = re.sub(r"[^\x00-\x7F]", "", candidate)
    # Step 3: collapse multiple dashes
    candidate = re.sub(r"-{2,}", "-", candidate).strip("-")

    parts = candidate.split("-")

    # Need at least 4 parts: 3 named + 1 numeric suffix
    if len(parts) < 4:
        # Cannot produce a meaningful suggestion without inventing segments
        return None

    # Check if the last part looks numeric (the suffix)
    *named, suffix = parts
    if not suffix.isdigit():
        # Last part isn't numeric — unrecoverable
        return None

    # Step 4: zero-pad suffix to 3 digits
    suffix = suffix.zfill(3)

    # We need exactly 3 named segments
    if len(named) != 3:
        return None

    # Validate each named segment matches [A-Z][A-Z0-9]*
    for seg in named:
        if not re.match(r"^[A-Z][A-Z0-9]*$", seg):
            return None

    return "-".join(named + [suffix])


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: tag_parser.py <TAG>")
        sys.exit(2)

    tag = sys.argv[1]
    ok, suggestion = validate(tag)

    if ok:
        print(f"✅ Valid: {tag}")
        sys.exit(0)
    else:
        if suggestion:
            print(f"❌ Invalid: {tag!r} — suggestion: {suggestion}")
        else:
            print(f"❌ Invalid: {tag!r} — structurally incorrect (need PROYECTO-SUBAREA-COMPONENTE-NNN)")
        sys.exit(1)


if __name__ == "__main__":
    main()
