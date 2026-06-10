#!/usr/bin/env python3
"""
mind_journal.py — Mind Journal task: seeding, recurrence, and entry logging.

A single auto-seeded task inside the SCRATCH-PAD project that prompts the user
every few hours (default 4, configurable, waking-hours only) to record what
their mind is thinking, what they are doing, and a mood. Each answer is appended
as a timestamped, mood-tagged entry inside the task body.

Public API:
    find_journal(vault_path)                     -> Path | None
    ensure_mind_journal(vault_path, vault_name)  -> None
    compute_due(frontmatter, now=None)           -> dict
    parse_entries(body)                          -> list[dict]
    read_journal(vault_path)                     -> dict
    append_entry(path, mind, doing, mood, now=None) -> None
    write_config(path, interval_hours=None, waking_start=None, waking_end=None) -> None

Specs: docs/ears/mind-journal-mood-check-in.md (R-1.x, R-2.x, R-3.x)
"""
from __future__ import annotations

import datetime
import logging
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from intent_parser import parse_frontmatter, parse_intent, write_frontmatter  # noqa: E402

_log = logging.getLogger("mind_journal")

# ── Constants ────────────────────────────────────────────────────────────────

JOURNAL_ID = "MIND-JOURNAL"
SCRATCH_PAD_SLUG = "SCRATCH-PAD"
PROJECTS_DIR = "01-Active-Projects"

DEFAULT_INTERVAL_HOURS = 4
DEFAULT_WAKING_START = "08:00"
DEFAULT_WAKING_END = "22:00"

VALID_MOODS = ("happy", "neutral", "sad")
MOOD_EMOJI = {"happy": "😊", "neutral": "😐", "sad": "😔"}

_SEEDED_FLAG = "mind_journal_seeded"
_HHMM_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
# "### 2026-06-03 14:00 · 😊 happy"
_ENTRY_HEADING_RE = re.compile(
    r"^###\s+(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2})\s+·\s+\S+\s+(\w+)\s*$"
)

_JOURNAL_TEMPLATE = """---
id: {id}
type: C
status: wip
created: {created_date}
project: {project}
journal: true
reminder_interval_hours: {interval}
reminder_last_logged: {created_ts}
waking_start: "{waking_start}"
waking_end: "{waking_end}"
tags: [task, journal]
---

# Mind Journal

A journal for your mind. Every few hours, jot down what you're thinking, what
you're doing, and how you feel. This task is yours — delete it anytime if you
don't want it.

## Entries
"""


# ── Time helpers ───────────────────────────────────────────────────────────────

def _now() -> datetime.datetime:
    return datetime.datetime.now().astimezone()


def _as_aware(dt: datetime.datetime) -> datetime.datetime:
    """Attach the local timezone to a naive datetime; leave aware ones alone."""
    if dt.tzinfo is None:
        return dt.astimezone()
    return dt


def _parse_dt(value) -> Optional[datetime.datetime]:
    """Parse an ISO timestamp or date string to an aware datetime, or None."""
    if not value:
        return None
    s = str(value).strip()
    try:
        return _as_aware(datetime.datetime.fromisoformat(s))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return _as_aware(datetime.datetime.strptime(s, fmt))
        except ValueError:
            continue
    return None


def _parse_hhmm(value, default: str) -> datetime.time:
    s = str(value).strip().strip('"').strip("'") if value is not None else ""
    m = _HHMM_RE.match(s)
    if not m:
        m = _HHMM_RE.match(default)
    return datetime.time(int(m.group(1)), int(m.group(2)))


def _interval_hours(fm: dict) -> float:
    raw = fm.get("reminder_interval_hours")
    try:
        val = float(raw)
        if val > 0:
            return val
    except (TypeError, ValueError):
        pass
    return float(DEFAULT_INTERVAL_HOURS)


# ── R-2.1 — Discovery by `journal: true` marker (not filename) ────────────────

def find_journal(vault_path: Path) -> Optional[Path]:
    """Return the journal task file (marked `journal: true`), or None.

    Searches the SCRATCH-PAD project first, then the whole projects tree, so a
    manual rename or move within projects does not orphan the journal.
    """
    vault_path = Path(vault_path)
    scratch = vault_path / PROJECTS_DIR / SCRATCH_PAD_SLUG
    search_roots = [scratch, vault_path / PROJECTS_DIR]
    seen: set[Path] = set()
    for root in search_roots:
        if not root.exists():
            continue
        for md in sorted(root.rglob("*.md")):
            if md in seen or md.name.startswith("."):
                continue
            seen.add(md)
            try:
                fm, _ = parse_frontmatter(md.read_text(encoding="utf-8"))
            except Exception:
                continue
            if str(fm.get("journal", "")).strip().lower() in ("true", "1", "yes"):
                return md
    return None


# ── R-1.x — Seeding (mandatory once, then deletable) ──────────────────────────

def _read_seeded_flag(vault_name: str) -> bool:
    try:
        import config_loader
        state = config_loader.read_state(vault_name)
        return bool(state.get(_SEEDED_FLAG))
    except Exception:
        return False


def _set_seeded_flag(vault_name: str) -> None:
    import config_loader
    state = config_loader.read_state(vault_name)
    state[_SEEDED_FLAG] = True
    config_loader.write_state(vault_name, state)


def ensure_mind_journal(vault_path: Path, vault_name: str) -> None:
    """Seed the Mind Journal task once per vault. No-op if already seeded.

    R-1.1 reads the `mind_journal_seeded` flag from vault state JSON.
    R-1.2/R-1.3 create the task file. R-1.4 records the flag. R-1.5 means a
    deleted journal is not resurrected. R-1.8 makes any failure non-fatal.
    """
    try:
        vault_path = Path(vault_path)
        if _read_seeded_flag(vault_name):  # R-1.5
            return
        project_dir = vault_path / PROJECTS_DIR / SCRATCH_PAD_SLUG
        project_dir.mkdir(parents=True, exist_ok=True)
        journal_path = project_dir / f"{JOURNAL_ID}.md"
        if not journal_path.exists():  # R-1.2
            now = _now()
            content = _JOURNAL_TEMPLATE.format(
                id=JOURNAL_ID,
                created_date=now.date().isoformat(),
                created_ts=now.isoformat(timespec="seconds"),
                project=SCRATCH_PAD_SLUG,
                interval=DEFAULT_INTERVAL_HOURS,
                waking_start=DEFAULT_WAKING_START,
                waking_end=DEFAULT_WAKING_END,
            )
            journal_path.write_text(content, encoding="utf-8")
        _set_seeded_flag(vault_name)  # R-1.4
    except Exception as exc:  # R-1.8 — non-fatal
        _log.warning("ensure_mind_journal failed: %s", exc)


# ── R-2.x — Recurrence & due computation (request-time, no scheduler) ─────────

def compute_due(fm: dict, now: Optional[datetime.datetime] = None) -> dict:
    """Compute the recurring check-in state from journal frontmatter.

    Returns {due, next_due, interval_hours, waking: {start, end}, last_logged}.
    """
    now = _as_aware(now) if now is not None else _now()
    interval = _interval_hours(fm)  # R-2.2
    waking_start = _parse_hhmm(fm.get("waking_start"), DEFAULT_WAKING_START)  # R-2.4
    waking_end = _parse_hhmm(fm.get("waking_end"), DEFAULT_WAKING_END)

    last = (
        _parse_dt(fm.get("reminder_last_logged"))
        or _parse_dt(fm.get("created"))
        or now
    )  # R-2.3
    boundary = last + datetime.timedelta(hours=interval)

    def in_window(t: datetime.time) -> bool:
        return waking_start <= t <= waking_end

    due = now >= boundary and in_window(now.time())  # R-2.5, R-2.6

    # R-2.7 — if the boundary lands outside the waking window, the next
    # surfacing is the start of the next waking window.
    if in_window(boundary.time()):
        next_due = boundary
    else:
        start_dt = datetime.datetime.combine(
            boundary.date(), waking_start, tzinfo=boundary.tzinfo
        )
        if start_dt < boundary:
            start_dt += datetime.timedelta(days=1)
        next_due = start_dt

    return {
        "due": due,
        "next_due": next_due.isoformat(timespec="seconds"),
        "interval_hours": interval,
        "waking": {
            "start": waking_start.strftime("%H:%M"),
            "end": waking_end.strftime("%H:%M"),
        },
        "last_logged": last.isoformat(timespec="seconds"),
    }


# ── Entry parsing & appending ──────────────────────────────────────────────────

def parse_entries(body: str) -> list[dict]:
    """Parse `### <ts> · <emoji> <mood>` blocks into ordered dicts."""
    lines = body.splitlines()
    entries: list[dict] = []
    current: Optional[dict] = None
    for line in lines:
        m = _ENTRY_HEADING_RE.match(line.strip())
        if m:
            current = {"timestamp": m.group(1), "mood": m.group(2).lower(),
                       "mind": "", "doing": ""}
            entries.append(current)
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("**Mind:**"):
            current["mind"] = stripped[len("**Mind:**"):].strip()
        elif stripped.startswith("**Doing:**"):
            current["doing"] = stripped[len("**Doing:**"):].strip()
    return entries  # chronological (oldest first) — R-3.11


def _split_doc(path: Path) -> tuple[str, str]:
    """Return (frontmatter_block_with_markers, body)."""
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return "", content
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            return "".join(lines[: i + 1]), "".join(lines[i + 1:])
    return "", content


def append_entry(
    path: Path,
    mind: str,
    doing: str,
    mood: str,
    now: Optional[datetime.datetime] = None,
) -> None:
    """Append a timestamped, mood-tagged entry under `## Entries` and advance
    the recurrence clock (`reminder_last_logged`).

    R-3.5, R-3.6, R-3.11. Caller validates `mood` against VALID_MOODS.
    """
    now = _as_aware(now) if now is not None else _now()
    mood = mood.lower()
    emoji = MOOD_EMOJI.get(mood, "")
    ts = now.strftime("%Y-%m-%d %H:%M")
    block = (
        f"### {ts} · {emoji} {mood}\n"
        f"**Mind:** {mind.strip()}\n"
        f"**Doing:** {doing.strip()}\n"
    )

    fm_block, body = _split_doc(path)
    body = body.rstrip("\n") + "\n\n" + block
    path.write_text(fm_block + body, encoding="utf-8")

    # R-3.6 — reset the recurrence clock.
    write_frontmatter(path, {"reminder_last_logged": now.isoformat(timespec="seconds")})


def write_config(
    path: Path,
    interval_hours=None,
    waking_start=None,
    waking_end=None,
) -> None:
    """Upsert recurrence config fields into the journal frontmatter (R-3.8).

    Caller validates inputs (R-3.9). Only provided fields are written.
    """
    updates: dict = {}
    if interval_hours is not None:
        updates["reminder_interval_hours"] = interval_hours
    if waking_start is not None:
        updates["waking_start"] = f'"{waking_start}"'
    if waking_end is not None:
        updates["waking_end"] = f'"{waking_end}"'
    if updates:
        write_frontmatter(path, updates)


# ── API aggregate ──────────────────────────────────────────────────────────────

def read_journal(vault_path: Path, now: Optional[datetime.datetime] = None) -> dict:
    """Build the GET /api/journal payload, or {'exists': False} (R-3.1, R-3.2)."""
    journal_path = find_journal(vault_path)
    if journal_path is None:
        return {"exists": False}
    data = parse_intent(journal_path)
    fm = data["frontmatter"]
    _, body = parse_frontmatter(journal_path.read_text(encoding="utf-8"))
    state = compute_due(fm, now=now)
    return {
        "exists": True,
        "task": {
            "id": data["id"],
            "title": data["title"],
            "path": str(journal_path),
        },
        "entries": parse_entries(body),
        "due": state["due"],
        "next_due": state["next_due"],
        "interval_hours": state["interval_hours"],
        "waking": state["waking"],
    }
