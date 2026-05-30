#!/usr/bin/env python3
"""
reminder_writer.py — Write/update reminder fields in intent file frontmatter
and body callout block.

Public API:
    resolve_reminder_date(value)   -> absolute YYYY-MM-DD string
    write_reminder_date(path, date) -> None  (upsert frontmatter + callout)
    dismiss_reminder(path)          -> None  (mark dismissed, remove callout)
    snooze_reminder(path, until)    -> None  (set snoozed_until, update callout)

Spec: R-1.1 – R-1.6
"""

import datetime
import os
import sys
from pathlib import Path

# Import from intent_parser (same lib/ directory)
sys.path.insert(0, str(Path(__file__).parent))
from intent_parser import write_frontmatter, _DELETE, parse_frontmatter  # noqa: E402

try:
    from dateutil.relativedelta import relativedelta as _rdelta  # type: ignore
    _HAS_RDELTA = True
except ImportError:
    _HAS_RDELTA = False

# ─────────────────────────────────────────────────────────────────────────────
# R-1.1 / R-1.2 — Date resolution
# ─────────────────────────────────────────────────────────────────────────────

_RELATIVE_MAP = {
    "in 1 month":  (dict(months=1),  30),
    "in 3 months": (dict(months=3),  91),
    "in 6 months": (dict(months=6), 182),
    "in 1 year":   (dict(years=1),  365),
}


def resolve_reminder_date(value: str) -> str:
    """Return absolute YYYY-MM-DD. Accepts absolute date or relative string.

    Supported relative strings: "in 1 month", "in 3 months", "in 6 months",
    "in 1 year".
    """
    value = value.strip()
    # Try absolute first
    try:
        datetime.date.fromisoformat(value)
        return value
    except ValueError:
        pass

    today = datetime.date.today()
    if value not in _RELATIVE_MAP:
        raise ValueError(f"Unrecognized reminder_date: {value!r}")

    kwargs, days_fallback = _RELATIVE_MAP[value]
    if _HAS_RDELTA:
        from dateutil.relativedelta import relativedelta
        result = today + relativedelta(**kwargs)
    else:
        result = today + datetime.timedelta(days=days_fallback)
    return result.isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Callout helpers
# ─────────────────────────────────────────────────────────────────────────────

_CALLOUT_PREFIX = "> 📅 **Reminder:**"


def _make_callout(date_str: str) -> str:
    return f"{_CALLOUT_PREFIX} {date_str}"


def _is_callout(line: str) -> bool:
    return line.startswith(_CALLOUT_PREFIX)


def _insert_or_update_callout(body: str, date_str: str) -> str:
    """Insert or replace the reminder callout in the body.

    Strategy:
    - Find the first `# ` heading line.
    - If the next non-empty line is already a callout: replace it.
    - Otherwise: insert after the title line.
    - If no `# ` heading found: prepend callout at start of body.
    """
    lines = body.splitlines(keepends=True)
    callout_line = _make_callout(date_str) + "\n"

    # Find title heading index
    title_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title_idx = i
            break

    if title_idx is None:
        # No heading — prepend callout at start of body
        # First remove any existing callout
        lines = [ln for ln in lines if not _is_callout(ln.rstrip("\n"))]
        return callout_line + "".join(lines)

    # Look at the line immediately after the title
    next_idx = title_idx + 1

    if next_idx < len(lines) and _is_callout(lines[next_idx].rstrip("\n")):
        # Replace existing callout
        lines[next_idx] = callout_line
    else:
        # Insert after title; also ensure any stale callout elsewhere is removed
        # first (shouldn't normally exist, but be safe)
        new_lines = []
        inserted = False
        for i, line in enumerate(lines):
            if i == title_idx:
                new_lines.append(line)
                new_lines.append(callout_line)
                inserted = True
            elif _is_callout(line.rstrip("\n")) and inserted:
                # Drop a stale callout that appeared elsewhere after insertion
                pass
            else:
                new_lines.append(line)
        lines = new_lines

    return "".join(lines)


def _remove_callout(body: str) -> str:
    """Remove all lines matching the reminder callout pattern."""
    lines = body.splitlines(keepends=True)
    lines = [ln for ln in lines if not _is_callout(ln.rstrip("\n"))]
    return "".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Body read/write helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_body(path: Path) -> str:
    """Return only the body text (after frontmatter closing `---`)."""
    content = path.read_text(encoding="utf-8")
    _, body = parse_frontmatter(content)
    return body


def _rewrite_body(path: Path, new_body: str) -> None:
    """Re-assemble the file with a new body and write atomically."""
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    # Locate the closing `---` of the frontmatter
    if not lines or lines[0].rstrip("\r\n") != "---":
        # No frontmatter — just rewrite the whole file as the body
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(new_body, encoding="utf-8")
        os.replace(tmp, path)
        return

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            end_idx = i
            break

    if end_idx is None:
        # Malformed frontmatter — no-op for body
        return

    frontmatter_part = "".join(lines[: end_idx + 1])
    new_content = frontmatter_part + new_body
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(new_content, encoding="utf-8")
    os.replace(tmp, path)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def write_reminder_date(path: Path, reminder_date: str) -> None:
    """Write/update reminder_date in frontmatter and callout in body.

    reminder_date may be absolute (YYYY-MM-DD) or relative ("in 1 month", …).
    R-1.1, R-1.2, R-1.3, R-1.4, R-1.5
    """
    abs_date = resolve_reminder_date(reminder_date)
    # Frontmatter: upsert reminder_date
    write_frontmatter(path, {"reminder_date": abs_date})
    # Body: insert or update callout
    body = _read_body(path)
    new_body = _insert_or_update_callout(body, abs_date)
    if new_body != body:
        _rewrite_body(path, new_body)


def dismiss_reminder(path: Path) -> None:
    """Mark reminder dismissed: set reminder_dismissed, remove reminder_date
    and reminder_snoozed_until from frontmatter. Remove callout from body.

    R-1.5
    """
    today_str = datetime.date.today().isoformat()
    write_frontmatter(path, {
        "reminder_dismissed": today_str,
        "reminder_date": _DELETE,
        "reminder_snoozed_until": _DELETE,
    })
    body = _read_body(path)
    new_body = _remove_callout(body)
    if new_body != body:
        _rewrite_body(path, new_body)


def snooze_reminder(path: Path, until_date: str) -> None:
    """Snooze reminder: set reminder_snoozed_until, clear reminder_dismissed.
    Update callout in body to the new date.

    R-1.5
    """
    abs_until = resolve_reminder_date(until_date)
    write_frontmatter(path, {
        "reminder_snoozed_until": abs_until,
        "reminder_dismissed": _DELETE,
    })
    body = _read_body(path)
    new_body = _insert_or_update_callout(body, abs_until)
    if new_body != body:
        _rewrite_body(path, new_body)
