"""
test_quick_task_scanner.py — Tests for quick_task_scanner.scan_quick_tasks (A.1).

Covers EARS R-2.1, R-2.2, R-2.6, R-2.7, R-4.1, R-4.5.

Fixtures are real QT-*.md files in a tmp vault's SCRATCH-PAD folder:
  01-Active-Projects/SCRATCH-PAD/
    QT-001.md  — active, qt_created_at oldest
    QT-002.md  — active, qt_created_at middle
    QT-003.md  — active, qt_created_at newest
    QT-004.md  — snoozed, qt_snoozed_until in the future   → snoozed, wake_due False
    QT-005.md  — snoozed, qt_snoozed_until in the past      → snoozed, wake_due True
    QT-006.md  — done                                       → excluded
    not_a_qt.md — intent file without quick_task: true      → ignored
"""

import datetime
import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

from quick_task_scanner import scan_quick_tasks


def _qt(stem: str, *, text: str, qt_state: str = "active",
        qt_created_at: str | None = None, qt_snoozed_until: str | None = None,
        status: str = "open") -> str:
    fields = {
        "id": stem,
        "type": "quick_task",
        "quick_task": "true",
        "qt_state": qt_state,
        "status": status,
    }
    if qt_created_at is not None:
        fields["qt_created_at"] = qt_created_at
    if qt_snoozed_until is not None:
        fields["qt_snoozed_until"] = qt_snoozed_until
    fm = "\n".join(f"{k}: {v}" for k, v in fields.items())
    return f"---\n{fm}\n---\n\n# {text}\n\n> ⚡ **Quick Task**\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    now = datetime.datetime.now()
    sp = tmp_path / "01-Active-Projects" / "SCRATCH-PAD"

    t_old = (now - datetime.timedelta(minutes=30)).isoformat()
    t_mid = (now - datetime.timedelta(minutes=20)).isoformat()
    t_new = (now - datetime.timedelta(minutes=10)).isoformat()
    future = (now + datetime.timedelta(hours=1)).isoformat()
    past = (now - datetime.timedelta(hours=1)).isoformat()

    _write(sp / "QT-001.md", _qt("QT-001", text="Oldest task", qt_created_at=t_old))
    _write(sp / "QT-002.md", _qt("QT-002", text="Middle task", qt_created_at=t_mid))
    _write(sp / "QT-003.md", _qt("QT-003", text="Newest task", qt_created_at=t_new))
    _write(sp / "QT-004.md", _qt("QT-004", text="Snoozed future",
                                 qt_state="snoozed", qt_snoozed_until=future))
    _write(sp / "QT-005.md", _qt("QT-005", text="Snoozed expired",
                                 qt_state="snoozed", qt_snoozed_until=past))
    _write(sp / "QT-006.md", _qt("QT-006", text="Done task",
                                 qt_state="done", status="done"))
    # A normal intent file that is NOT a quick task — must be ignored.
    _write(sp / "not_a_qt.md",
           "---\nid: TASK-9\ntype: T\nstatus: wip\n---\n\n# Normal intent\n")
    return tmp_path


def test_active_sorted_oldest_first(vault):
    """R-2.1 / R-2.7: active tasks are FIFO, oldest qt_created_at first."""
    result = scan_quick_tasks(vault)
    ids = [t["id"] for t in result["active"]]
    assert ids == ["QT-001", "QT-002", "QT-003"]


def test_active_count_excludes_snoozed_and_done(vault):
    """R-2.2 / R-2.6: active_count counts only qt_state == active."""
    result = scan_quick_tasks(vault)
    assert result["active_count"] == 3


def test_done_excluded_entirely(vault):
    """R-2.6: done tasks appear in neither bucket."""
    result = scan_quick_tasks(vault)
    all_ids = [t["id"] for t in result["active"]] + [t["id"] for t in result["snoozed"]]
    assert "QT-006" not in all_ids


def test_snoozed_bucket_kept_visible_with_wake_flags(vault):
    """R-4.1 / R-4.5: snoozed tasks stay visible; wake_due reflects the wake time."""
    result = scan_quick_tasks(vault)
    by_id = {t["id"]: t for t in result["snoozed"]}
    assert set(by_id) == {"QT-004", "QT-005"}
    assert by_id["QT-004"]["wake_due"] is False   # future
    assert by_id["QT-005"]["wake_due"] is True    # expired → eligible to return


def test_non_quick_task_files_ignored(vault):
    """Only quick_task: true files are scanned."""
    result = scan_quick_tasks(vault)
    all_ids = [t["id"] for t in result["active"]] + [t["id"] for t in result["snoozed"]]
    assert "TASK-9" not in all_ids


def test_text_comes_from_title(vault):
    """The captured one-line text is surfaced as `text`."""
    result = scan_quick_tasks(vault)
    assert result["active"][0]["text"] == "Oldest task"


def test_empty_vault_is_safe(tmp_path):
    """No SCRATCH-PAD folder → empty result, no error."""
    result = scan_quick_tasks(tmp_path)
    assert result["active"] == []
    assert result["snoozed"] == []
    assert result["active_count"] == 0


def test_aware_snoozed_until_does_not_crash(tmp_path):
    """M6/M7 audit fix: offset-bearing qt_snoozed_until (written by the
    aware-everywhere writer) classifies without a naive/aware TypeError."""
    now = datetime.datetime.now().astimezone()
    sp = tmp_path / "01-Active-Projects" / "SCRATCH-PAD"
    future = (now + datetime.timedelta(hours=1)).isoformat()
    past = (now - datetime.timedelta(hours=1)).isoformat()
    assert "+" in future or "-" in future[-6:]  # really carries an offset
    _write(sp / "QT-101.md", _qt("QT-101", text="Aware future",
                                 qt_state="snoozed", qt_snoozed_until=future))
    _write(sp / "QT-102.md", _qt("QT-102", text="Aware past",
                                 qt_state="snoozed", qt_snoozed_until=past))
    result = scan_quick_tasks(tmp_path)
    by_id = {t["id"]: t for t in result["snoozed"]}
    assert by_id["QT-101"]["wake_due"] is False
    assert by_id["QT-102"]["wake_due"] is True


def test_naive_and_aware_snoozed_until_coexist(tmp_path):
    """Old naive frontmatter and new aware frontmatter classify side by side."""
    now = datetime.datetime.now()
    sp = tmp_path / "01-Active-Projects" / "SCRATCH-PAD"
    naive_past = (now - datetime.timedelta(hours=1)).isoformat()
    aware_future = (now.astimezone() + datetime.timedelta(hours=1)).isoformat()
    _write(sp / "QT-201.md", _qt("QT-201", text="Naive past",
                                 qt_state="snoozed", qt_snoozed_until=naive_past))
    _write(sp / "QT-202.md", _qt("QT-202", text="Aware future",
                                 qt_state="snoozed", qt_snoozed_until=aware_future))
    result = scan_quick_tasks(tmp_path)
    by_id = {t["id"]: t for t in result["snoozed"]}
    assert by_id["QT-201"]["wake_due"] is True
    assert by_id["QT-202"]["wake_due"] is False
