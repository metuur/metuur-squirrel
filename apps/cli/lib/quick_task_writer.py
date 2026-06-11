#!/usr/bin/env python3
"""
quick_task_writer.py — Create and mutate Quick Task files in SCRATCH-PAD.

Quick Tasks are small (2–5 min) interruptions parked in a FIFO stack of at most
MAX_ACTIVE active items. Each is a markdown file in
01-Active-Projects/SCRATCH-PAD/ named QT-NNN.md with:

    type: quick_task
    quick_task: true
    qt_state: active | snoozed | done
    qt_created_at: <ISO timestamp>      # FIFO ordering key
    qt_snoozed_until: <ISO timestamp>   # present only while snoozed
    qt_snooze_count: <int>
    status: open | done

Public API (this story, A.2):
    create_quick_task(vault_path, text) -> str   # returns the new id (QT-NNN)

Cap enforcement (R-2.3, R-2.5, R-6.6): the live active count is read immediately
before the cap check via quick_task_scanner — never a cached value.

Spec: R-1.2, R-1.7, R-2.3, R-2.5, R-6.3, R-6.4, R-6.6
"""

from __future__ import annotations

import datetime
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from quick_task_scanner import scan_quick_tasks  # noqa: E402
from intent_parser import write_frontmatter, _DELETE, parse_intent  # noqa: E402
from fs_atomic import atomic_write_text  # noqa: E402

MAX_ACTIVE = 5
MAX_SNOOZES = 2

SCRATCH_PAD_DIR = Path("01-Active-Projects") / "SCRATCH-PAD"
_ID_PREFIX = "QT"


class QuickTaskError(Exception):
    """Raised when a Quick Task operation cannot proceed. Carries a stable code."""

    def __init__(self, code: str, message: str | None = None) -> None:
        self.code = code
        super().__init__(message or code)


def _scratch_pad_dir(vault_path: Path) -> Path:
    return Path(vault_path).expanduser().resolve() / SCRATCH_PAD_DIR


def _next_number(folder: Path, prefix: str) -> int:
    """Smallest N such that `<prefix>-<NNN>.md` is unused in `folder`.

    Done/snoozed Quick Task files are retained, so their numbers stay reserved —
    ids are never reused (R-1.7).
    """
    used: set[int] = set()
    pat = re.compile(re.escape(prefix) + r"-(\d{3})\.md$", re.IGNORECASE)
    if folder.exists():
        for entry in folder.glob(f"{prefix}-*.md"):
            m = pat.search(entry.name)
            if m:
                used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return n


def _atomic_write(target: Path, body: str) -> None:
    """Write atomically within the target folder (temp + fsync + os.replace)."""
    atomic_write_text(target, body)


def _format_quick_task(*, qt_id: str, text: str, created_iso: str) -> str:
    parked = created_iso.split("T")[0]
    return (
        "---\n"
        f"id: {qt_id}\n"
        "project: SCRATCH-PAD\n"
        "type: quick_task\n"
        "quick_task: true\n"
        "qt_state: active\n"
        f"qt_created_at: {created_iso}\n"
        "qt_snooze_count: 0\n"
        "status: open\n"
        "---\n\n"
        f"# {text}\n\n"
        f"> ⚡ **Quick Task** · parked {parked}\n"
    )


def create_quick_task(vault_path: Path, text: str) -> str:
    """Create a new active Quick Task. Returns the new id (e.g. "QT-003").

    Raises QuickTaskError("QUICK_TASK_LIMIT_REACHED") when the stack already holds
    MAX_ACTIVE active tasks (R-2.3). The active count is read live just before the
    check (R-6.6).
    """
    if not text or not text.strip():
        raise QuickTaskError("EMPTY_TEXT", "quick task text must be non-empty")

    vault_path = Path(vault_path).expanduser().resolve()

    # R-6.6: live count immediately before the cap gate.
    if scan_quick_tasks(vault_path)["active_count"] >= MAX_ACTIVE:
        raise QuickTaskError("QUICK_TASK_LIMIT_REACHED")

    folder = _scratch_pad_dir(vault_path)
    folder.mkdir(parents=True, exist_ok=True)

    nnn = _next_number(folder, _ID_PREFIX)
    qt_id = f"{_ID_PREFIX}-{nnn:03d}"
    target = folder / f"{qt_id}.md"

    # Microsecond precision keeps qt_created_at a strict FIFO key even when tasks
    # are captured within the same second (the callout shows only the date).
    now = datetime.datetime.now().astimezone()
    body = _format_quick_task(qt_id=qt_id, text=text.strip(), created_iso=now.isoformat())

    _atomic_write(target, body)
    return qt_id


# ─────────────────────────────────────────────────────────────────────────────
# A.3 — complete / delete
# ─────────────────────────────────────────────────────────────────────────────

def resolve_quick_task_path(vault_path: Path, qt_id: str) -> Path | None:
    """Resolve a Quick Task id to its file under SCRATCH-PAD, or None.

    R-6.4: only ever resolves inside SCRATCH-PAD, never elsewhere in the vault.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", qt_id or ""):
        return None
    candidate = _scratch_pad_dir(vault_path) / f"{qt_id}.md"
    return candidate if candidate.exists() else None


def complete_quick_task(path: Path) -> None:
    """Mark a Quick Task done. Frees an active slot (R-3.1)."""
    write_frontmatter(Path(path), {"qt_state": "done", "status": "done"})


def delete_quick_task(path: Path) -> None:
    """Remove a Quick Task file. Frees an active slot (R-3.2)."""
    Path(path).unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# A.4 — snooze + duration resolution
# ─────────────────────────────────────────────────────────────────────────────

def resolve_snooze_until(value: str | None) -> str:
    """Resolve a snooze duration to an absolute ISO-8601 timestamp (R-3.4).

    Accepts:
      "15m"          -> now + 15 minutes
      "1h" (default) -> now + 1 hour
      "next_block"   -> next focus-block boundary (next noon if morning, else
                        next midnight)
      a bare ISO date/datetime string -> passed through (normalized)
    """
    now = datetime.datetime.now().astimezone().replace(microsecond=0)
    v = (value or "1h").strip()

    if v == "15m":
        return (now + datetime.timedelta(minutes=15)).isoformat()
    if v == "1h":
        return (now + datetime.timedelta(hours=1)).isoformat()
    if v == "next_block":
        noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
        if now < noon:
            target = noon
        else:
            midnight = (now + datetime.timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            target = midnight
        return target.isoformat()

    # Bare ISO passthrough (date or datetime), normalized to an aware local
    # timestamp so scanner comparisons never mix naive and aware datetimes.
    try:
        dt = datetime.datetime.fromisoformat(v.replace("Z", ""))
    except ValueError:
        try:
            d = datetime.date.fromisoformat(v)
            dt = datetime.datetime(d.year, d.month, d.day)
        except ValueError:
            raise QuickTaskError("BAD_SNOOZE_UNTIL", f"unrecognized snooze value: {v!r}")
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.isoformat()


def _snooze_count(path: Path) -> int:
    fm = parse_intent(Path(path))["frontmatter"]
    try:
        return int(fm.get("qt_snooze_count", 0) or 0)
    except (ValueError, TypeError):
        return 0


def snooze_quick_task(path: Path, until: str | None = "1h") -> str:
    """Snooze a Quick Task. Frees an active slot and returns the wake timestamp.

    Raises QuickTaskError("QUICK_TASK_SNOOZE_LIMIT") once the task has already
    been snoozed MAX_SNOOZES times (R-3.5).
    """
    path = Path(path)
    if _snooze_count(path) >= MAX_SNOOZES:
        raise QuickTaskError("QUICK_TASK_SNOOZE_LIMIT")

    wake_iso = resolve_snooze_until(until)
    write_frontmatter(path, {
        "qt_state": "snoozed",
        "qt_snoozed_until": wake_iso,
        "qt_snooze_count": _snooze_count(path) + 1,
    })
    return wake_iso


# ─────────────────────────────────────────────────────────────────────────────
# B.1 — capacity-aware wake-commit + payload assembly
# ─────────────────────────────────────────────────────────────────────────────

def collect_quick_tasks(vault_path: Path) -> dict:
    """Scan the stack, reactivate due snoozed tasks while capacity allows, and
    return the full payload for the API.

    Wake-commit (R-4.2, R-4.3, R-4.4): due snoozed tasks (wake time passed) are
    activated in ascending wake-time order while active_count < MAX_ACTIVE. Each
    activation re-stamps qt_created_at so the task re-enters at the bottom. Any
    still-due snoozed task that cannot fit stays snoozed and is flagged
    `return_blocked` — the cap is never exceeded.

    Returns:
        {
          "active": [...],         # oldest-first
          "snoozed": [...],        # each with `return_blocked`
          "active_count": int,
          "snoozed_count": int,
          "limit": MAX_ACTIVE,
          "return_blocked": bool,  # any snoozed task waiting for a slot
        }
    """
    vault_path = Path(vault_path).expanduser().resolve()
    scanned = scan_quick_tasks(vault_path)

    due = sorted(
        (t for t in scanned["snoozed"] if t.get("wake_due")),
        key=lambda t: t.get("qt_snoozed_until") or "",
    )
    slots = max(0, MAX_ACTIVE - scanned["active_count"])
    activated = 0
    for t in due:
        if activated >= slots:
            break
        path = t.get("path")
        if path:
            activate_quick_task(Path(path))
            activated += 1

    if activated:
        scanned = scan_quick_tasks(vault_path)

    any_blocked = False
    for t in scanned["snoozed"]:
        blocked = bool(t.get("wake_due"))
        t["return_blocked"] = blocked
        any_blocked = any_blocked or blocked

    return {
        "active": scanned["active"],
        "snoozed": scanned["snoozed"],
        "active_count": scanned["active_count"],
        "snoozed_count": len(scanned["snoozed"]),
        "limit": MAX_ACTIVE,
        "return_blocked": any_blocked,
    }


# ─────────────────────────────────────────────────────────────────────────────
# A.5 — activate (wake re-stamp)
# ─────────────────────────────────────────────────────────────────────────────

def activate_quick_task(path: Path) -> None:
    """Reactivate a snoozed Quick Task, re-stamping qt_created_at so it re-enters
    at the bottom of the FIFO stack (R-4.2)."""
    now = datetime.datetime.now().astimezone()
    write_frontmatter(Path(path), {
        "qt_state": "active",
        "qt_snoozed_until": _DELETE,
        "qt_created_at": now.isoformat(),
    })


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(prog="quick_task_writer")
    p.add_argument("--vault", required=True)
    p.add_argument("text")
    args = p.parse_args()
    try:
        new_id = create_quick_task(Path(args.vault), args.text)
        print(new_id)
    except QuickTaskError as e:
        print(f"error: {e.code}", file=sys.stderr)
        sys.exit(1)
