"""
test_quick_task_writer.py — Tests for quick_task_writer (A.2: create + hard cap).

Covers EARS R-1.2, R-1.7, R-2.3, R-2.5, R-6.3, R-6.4, R-6.6.
"""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

from quick_task_writer import (
    MAX_ACTIVE,
    QuickTaskError,
    create_quick_task,
)
from quick_task_scanner import scan_quick_tasks


def _sp(vault: Path) -> Path:
    return vault / "01-Active-Projects" / "SCRATCH-PAD"


def test_create_writes_file_with_expected_frontmatter(tmp_path):
    """R-1.2: create writes QT-001.md with the quick-task frontmatter + body text."""
    qt_id = create_quick_task(tmp_path, "Send Q2 attachment to Ana")
    assert qt_id == "QT-001"
    f = _sp(tmp_path) / "QT-001.md"
    assert f.exists()
    content = f.read_text(encoding="utf-8")
    assert "type: quick_task" in content
    assert "quick_task: true" in content
    assert "qt_state: active" in content
    assert "qt_snooze_count: 0" in content
    assert "qt_created_at:" in content
    assert "# Send Q2 attachment to Ana" in content


def test_create_appears_as_active_in_scanner(tmp_path):
    """R-2.5: a newly created task is active and counts toward the cap."""
    create_quick_task(tmp_path, "Approve transaction")
    result = scan_quick_tasks(tmp_path)
    assert result["active_count"] == 1
    assert result["active"][0]["text"] == "Approve transaction"


def test_sequential_ids_are_distinct_and_not_reused(tmp_path):
    """R-1.7: sequential creates get distinct, non-reused ids."""
    ids = [create_quick_task(tmp_path, f"Task {i}") for i in range(3)]
    assert ids == ["QT-001", "QT-002", "QT-003"]


def test_sixth_create_is_blocked(tmp_path):
    """R-2.3: with MAX_ACTIVE active, a further create raises the cap error."""
    for i in range(MAX_ACTIVE):
        create_quick_task(tmp_path, f"Task {i}")
    with pytest.raises(QuickTaskError) as exc:
        create_quick_task(tmp_path, "One too many")
    assert exc.value.code == "QUICK_TASK_LIMIT_REACHED"
    # No 6th file written.
    qt_files = list(_sp(tmp_path).glob("QT-*.md"))
    assert len(qt_files) == MAX_ACTIVE


def test_empty_text_rejected(tmp_path):
    """Empty/whitespace text is rejected, no file written."""
    with pytest.raises(QuickTaskError) as exc:
        create_quick_task(tmp_path, "   ")
    assert exc.value.code == "EMPTY_TEXT"
    assert not _sp(tmp_path).exists() or not list(_sp(tmp_path).glob("QT-*.md"))


def test_write_target_is_within_scratch_pad(tmp_path):
    """R-6.4: the file is created under SCRATCH-PAD, nowhere else."""
    create_quick_task(tmp_path, "Reply to email")
    assert (_sp(tmp_path) / "QT-001.md").exists()
    # Nothing leaked outside SCRATCH-PAD.
    others = [p for p in tmp_path.rglob("QT-*.md") if "SCRATCH-PAD" not in str(p)]
    assert others == []
