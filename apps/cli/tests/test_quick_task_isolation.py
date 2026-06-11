"""
test_quick_task_isolation.py — Quick Tasks are invisible to existing scanners (F.1).

Covers EARS R-6.1, R-6.2: intent/WIP (status_aggregator), deadline, and reminder
scanners must never surface or count type: quick_task files.
"""

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

from quick_task_writer import create_quick_task
from new_project_writer import ensure_scratch_pad
from status_aggregator import find_intents_for_project, analyze_project
from deadline_scanner import scan_vault_deadlines
from reminder_scanner import scan_vault_reminders


def _scratch_page(vault: Path) -> Path:
    return vault / "01-Active-Projects" / "SCRATCH-PAD" / "SCRATCH-PAD.md"


def _make_vault(tmp_path: Path) -> Path:
    ensure_scratch_pad(tmp_path)
    for t in ("Send attachment", "Approve transaction", "Reply to email"):
        create_quick_task(tmp_path, t)
    return tmp_path


def test_quick_tasks_not_counted_as_intents(tmp_path):
    """R-6.1: QT files are excluded from the intent list of SCRATCH-PAD."""
    vault = _make_vault(tmp_path)
    intents = find_intents_for_project(_scratch_page(vault))
    assert [p.name for p in intents] == []


def test_real_intent_still_counted_alongside_quick_tasks(tmp_path):
    """The exclusion is selective — a normal note in SCRATCH-PAD is still an intent."""
    vault = _make_vault(tmp_path)
    real = _scratch_page(vault).parent / "REAL-NOTE.md"
    real.write_text("---\nid: REAL-NOTE\ntype: capture\nstatus: pending\n---\n\n# Real\n",
                    encoding="utf-8")
    intents = find_intents_for_project(_scratch_page(vault))
    assert [p.name for p in intents] == ["REAL-NOTE.md"]


def test_analyze_project_intent_total_excludes_quick_tasks(tmp_path):
    """R-6.2: SCRATCH-PAD's intent total is 0 despite 3 quick tasks present."""
    vault = _make_vault(tmp_path)
    result = analyze_project(_scratch_page(vault))
    assert result["intents"]["total"] == 0


def test_quick_tasks_absent_from_deadline_scan(tmp_path):
    """R-6.1: QT files (no deadline) never appear in the deadline scanner."""
    vault = _make_vault(tmp_path)
    data = scan_vault_deadlines(vault)
    flat = [e["id"] for v in data.values() if isinstance(v, list) for e in v
            if isinstance(e, dict) and "id" in e]
    assert not any(i.startswith("QT-") for i in flat)


def test_quick_tasks_absent_from_reminder_scan(tmp_path):
    """R-6.1: QT files (no reminder_date) never appear in the reminder scanner."""
    vault = _make_vault(tmp_path)
    data = scan_vault_reminders(vault)
    ids = [e["id"] for e in data["approaching"] + data["active"]]
    assert not any(i.startswith("QT-") for i in ids)
