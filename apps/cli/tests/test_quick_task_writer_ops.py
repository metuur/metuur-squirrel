"""
test_quick_task_writer_ops.py — complete/delete/snooze/activate (A.3, A.4, A.5).

Covers EARS R-3.1, R-3.2, R-3.3, R-3.4, R-3.5, R-3.6, R-4.2.
"""

import datetime
import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

from quick_task_writer import (
    MAX_SNOOZES,
    QuickTaskError,
    activate_quick_task,
    complete_quick_task,
    create_quick_task,
    delete_quick_task,
    resolve_quick_task_path,
    resolve_snooze_until,
    snooze_quick_task,
)
from quick_task_scanner import scan_quick_tasks
from intent_parser import write_frontmatter, parse_intent


def _path(vault: Path, qt_id: str) -> Path:
    return vault / "01-Active-Projects" / "SCRATCH-PAD" / f"{qt_id}.md"


# ── A.3: complete / delete ───────────────────────────────────────────────────

def test_complete_marks_done_and_frees_slot(tmp_path):
    """R-3.1 / R-3.6: complete sets done state and drops the active count."""
    for i in range(3):
        create_quick_task(tmp_path, f"Task {i}")
    complete_quick_task(_path(tmp_path, "QT-001"))
    fm = parse_intent(_path(tmp_path, "QT-001"))["frontmatter"]
    assert str(fm["qt_state"]) == "done"
    assert str(fm["status"]) == "done"
    assert scan_quick_tasks(tmp_path)["active_count"] == 2


def test_delete_removes_file_and_frees_slot(tmp_path):
    """R-3.2 / R-3.6: delete removes the file and drops the active count."""
    for i in range(3):
        create_quick_task(tmp_path, f"Task {i}")
    delete_quick_task(_path(tmp_path, "QT-002"))
    assert not _path(tmp_path, "QT-002").exists()
    assert scan_quick_tasks(tmp_path)["active_count"] == 2


def test_resolve_path_rejects_unknown_and_traversal(tmp_path):
    """R-6.4: resolver only returns existing files inside SCRATCH-PAD."""
    create_quick_task(tmp_path, "Task")
    assert resolve_quick_task_path(tmp_path, "QT-001") == _path(tmp_path, "QT-001")
    assert resolve_quick_task_path(tmp_path, "QT-999") is None
    assert resolve_quick_task_path(tmp_path, "../../etc/passwd") is None


# ── A.4: snooze + resolution ─────────────────────────────────────────────────

def test_snooze_moves_to_snoozed_and_frees_slot(tmp_path):
    """R-3.3: snooze removes the task from active and records the wake time."""
    create_quick_task(tmp_path, "Task A")
    create_quick_task(tmp_path, "Task B")
    snooze_quick_task(_path(tmp_path, "QT-001"), "1h")
    result = scan_quick_tasks(tmp_path)
    assert result["active_count"] == 1
    snoozed_ids = [t["id"] for t in result["snoozed"]]
    assert snoozed_ids == ["QT-001"]
    fm = parse_intent(_path(tmp_path, "QT-001"))["frontmatter"]
    assert int(fm["qt_snooze_count"]) == 1


def test_snooze_limit_blocks_past_max(tmp_path):
    """R-3.5: once snoozed MAX_SNOOZES times, further snooze is rejected."""
    create_quick_task(tmp_path, "Task A")
    # Force the count to the cap directly, then attempt one more snooze.
    write_frontmatter(_path(tmp_path, "QT-001"), {"qt_snooze_count": MAX_SNOOZES})
    with pytest.raises(QuickTaskError) as exc:
        snooze_quick_task(_path(tmp_path, "QT-001"), "1h")
    assert exc.value.code == "QUICK_TASK_SNOOZE_LIMIT"


def test_resolve_snooze_until_durations():
    """R-3.4: durations resolve to absolute timestamps."""
    now = datetime.datetime.now()
    in_1h = datetime.datetime.fromisoformat(resolve_snooze_until("1h"))
    assert abs((in_1h - now).total_seconds() - 3600) < 5

    in_15m = datetime.datetime.fromisoformat(resolve_snooze_until("15m"))
    assert abs((in_15m - now).total_seconds() - 900) < 5

    # default (None) behaves like "1h"
    default = datetime.datetime.fromisoformat(resolve_snooze_until(None))
    assert abs((default - now).total_seconds() - 3600) < 5


def test_resolve_snooze_until_next_block():
    """R-3.4: next_block resolves to the next noon or next midnight boundary."""
    blk = datetime.datetime.fromisoformat(resolve_snooze_until("next_block"))
    assert (blk.hour, blk.minute, blk.second) in {(12, 0, 0), (0, 0, 0)}
    assert blk > datetime.datetime.now()


def test_resolve_snooze_until_iso_passthrough():
    """R-3.4: a bare ISO value is normalized and passed through."""
    out = resolve_snooze_until("2026-08-01")
    assert out.startswith("2026-08-01")


# ── A.5: activate (wake re-stamp) ────────────────────────────────────────────

def test_activate_restamps_created_at_to_bottom(tmp_path):
    """R-4.2: activating a snoozed task re-stamps qt_created_at to now and clears
    the snooze, so it re-enters at the bottom of the FIFO stack."""
    create_quick_task(tmp_path, "Oldest")          # QT-001
    create_quick_task(tmp_path, "Second")          # QT-002
    snooze_quick_task(_path(tmp_path, "QT-001"), "1h")

    before = parse_intent(_path(tmp_path, "QT-001"))["frontmatter"]
    activate_quick_task(_path(tmp_path, "QT-001"))
    after = parse_intent(_path(tmp_path, "QT-001"))["frontmatter"]

    assert str(after["qt_state"]) == "active"
    assert "qt_snoozed_until" not in after
    # Re-stamped created_at is newer than QT-002's, so it sorts last.
    result = scan_quick_tasks(tmp_path)
    assert [t["id"] for t in result["active"]] == ["QT-002", "QT-001"]
    assert str(after["qt_created_at"]) >= str(before.get("qt_created_at", ""))
