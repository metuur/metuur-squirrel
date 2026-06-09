"""
test_quick_task_collect.py — wake-commit + payload assembly (B.1 logic).

Covers EARS R-2.1, R-2.7, R-4.2, R-4.3, R-4.4, R-4.5.
"""

import datetime
import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

from quick_task_writer import (
    MAX_ACTIVE,
    collect_quick_tasks,
    create_quick_task,
    snooze_quick_task,
)


def _path(vault: Path, qt_id: str) -> Path:
    return vault / "01-Proyectos-Activos" / "SCRATCH-PAD" / f"{qt_id}.md"


def _past_iso() -> str:
    return (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat()


def _future_iso() -> str:
    return (datetime.datetime.now() + datetime.timedelta(hours=2)).isoformat()


def test_due_snoozed_returns_to_bottom_when_capacity(tmp_path):
    """R-4.2 / R-4.4: 4 active + 1 expired-snoozed → 5 active, woken one at bottom."""
    for i in range(5):
        create_quick_task(tmp_path, f"Task {i}")          # QT-001..005
    snooze_quick_task(_path(tmp_path, "QT-005"), _past_iso())  # 4 active + 1 due

    result = collect_quick_tasks(tmp_path)
    assert result["active_count"] == 5
    assert [t["id"] for t in result["active"]][-1] == "QT-005"  # re-entered at bottom
    assert result["snoozed_count"] == 0
    assert result["return_blocked"] is False
    assert result["limit"] == MAX_ACTIVE


def test_due_snoozed_blocked_when_full(tmp_path):
    """R-4.3: 5 active + 1 expired-snoozed → cap not breached, return_blocked set."""
    for i in range(5):
        create_quick_task(tmp_path, f"Task {i}")          # QT-001..005
    snooze_quick_task(_path(tmp_path, "QT-001"), _past_iso())  # 4 active + 1 due
    create_quick_task(tmp_path, "Refill")                 # QT-006 → 5 active + 1 due

    result = collect_quick_tasks(tmp_path)
    assert result["active_count"] == 5                    # cap honored
    assert result["snoozed_count"] == 1
    blocked = [t for t in result["snoozed"] if t["return_blocked"]]
    assert [t["id"] for t in blocked] == ["QT-001"]
    assert result["return_blocked"] is True


def test_future_snoozed_stays_and_not_blocked(tmp_path):
    """R-4.1 / R-4.5: a not-yet-due snoozed task stays snoozed, not blocked."""
    create_quick_task(tmp_path, "Active one")
    create_quick_task(tmp_path, "To snooze")              # QT-002
    snooze_quick_task(_path(tmp_path, "QT-002"), _future_iso())

    result = collect_quick_tasks(tmp_path)
    assert result["active_count"] == 1
    assert result["snoozed_count"] == 1
    assert result["snoozed"][0]["return_blocked"] is False
    assert result["return_blocked"] is False


def test_empty_stack(tmp_path):
    result = collect_quick_tasks(tmp_path)
    assert result == {
        "active": [],
        "snoozed": [],
        "active_count": 0,
        "snoozed_count": 0,
        "limit": MAX_ACTIVE,
        "return_blocked": False,
    }
