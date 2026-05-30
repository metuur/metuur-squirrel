"""
test_reminder_scanner.py — Tests for reminder_scanner.scan_vault_reminders (R-2.1–R-2.7).

Fixtures are real .md files in a tmp vault directory:
  01-Proyectos-Activos/PROJ-A/
    no_reminder.md          — no reminder_date field
    active_today.md         — reminder_date: <today>
    active_past.md          — reminder_date: <yesterday>
    approaching_3d.md       — reminder_date: <today + 3 days>
    far_future.md           — reminder_date: <today + 30 days>
    dismissed.md            — reminder_date: <today>, reminder_dismissed: 2026-01-01
    snoozed_future.md       — reminder_date: <today>, reminder_snoozed_until: <today + 10 days>
    snoozed_expired.md      — reminder_date: <today>, reminder_snoozed_until: <yesterday>  → active
    done_with_reminder.md   — reminder_date: <today>, estado: done
"""

import datetime
import sys
from pathlib import Path

import pytest

# Ensure lib is on the path (same pattern as deadline_scanner and its tests)
LIB_DIR = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

from reminder_scanner import scan_vault_reminders


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _md(stem: str, extra_fields: dict | None = None, reminder_date: str | None = None) -> str:
    """Build a minimal but valid frontmatter + body markdown string."""
    today = datetime.date.today().isoformat()
    fields = {
        "id": stem,
        "title": "Test Item",
        "proyecto": "PROJ-A",
        "estado": "wip",
    }
    if reminder_date is not None:
        fields["reminder_date"] = reminder_date
    if extra_fields:
        fields.update(extra_fields)

    fm_lines = "\n".join(f"{k}: {v}" for k, v in fields.items())
    return f"---\n{fm_lines}\n---\n\n# Test Item\n\nBody text.\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: vault with all test cases
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def vault(tmp_path: Path) -> Path:
    today = datetime.date.today()
    yesterday = (today - datetime.timedelta(days=1)).isoformat()
    tomorrow = (today + datetime.timedelta(days=1)).isoformat()
    in_3d = (today + datetime.timedelta(days=3)).isoformat()
    in_7d = (today + datetime.timedelta(days=7)).isoformat()
    in_10d = (today + datetime.timedelta(days=10)).isoformat()
    in_30d = (today + datetime.timedelta(days=30)).isoformat()
    today_str = today.isoformat()

    proj_dir = tmp_path / "01-Proyectos-Activos" / "PROJ-A"

    # no reminder_date field
    _write(proj_dir / "no_reminder.md", _md("no_reminder"))

    # active: today
    _write(proj_dir / "active_today.md", _md("active_today", reminder_date=today_str))

    # active: yesterday (past)
    _write(proj_dir / "active_past.md", _md("active_past", reminder_date=yesterday))

    # approaching: 3 days out
    _write(proj_dir / "approaching_3d.md", _md("approaching_3d", reminder_date=in_3d))

    # far future: 30 days (excluded)
    _write(proj_dir / "far_future.md", _md("far_future", reminder_date=in_30d))

    # dismissed: reminder_dismissed set → excluded
    _write(proj_dir / "dismissed.md", _md(
        "dismissed",
        reminder_date=today_str,
        extra_fields={"reminder_dismissed": "2026-01-01"},
    ))

    # snoozed_future: reminder_snoozed_until in the future → excluded
    _write(proj_dir / "snoozed_future.md", _md(
        "snoozed_future",
        reminder_date=today_str,
        extra_fields={"reminder_snoozed_until": in_10d},
    ))

    # snoozed_expired: snooze date in the past → active (snooze expired)
    _write(proj_dir / "snoozed_expired.md", _md(
        "snoozed_expired",
        reminder_date=today_str,
        extra_fields={"reminder_snoozed_until": yesterday},
    ))

    # done_with_reminder: estado: done → excluded (R-2.2)
    _write(proj_dir / "done_with_reminder.md", _md(
        "done_with_reminder",
        reminder_date=today_str,
        extra_fields={"estado": "done"},
    ))

    # Also add a file in 03-Areas to verify that location is scanned (R-2.1)
    areas_dir = tmp_path / "03-Areas" / "AREA-X"
    _write(areas_dir / "area_active.md", _md("area_active", reminder_date=today_str))

    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_return_shape(vault: Path) -> None:
    """Result has the required top-level keys."""
    result = scan_vault_reminders(vault)
    assert "scanned_at" in result
    assert "vault_path" in result
    assert "approaching" in result
    assert "active" in result


def test_active_contains_expected_items(vault: Path) -> None:
    """active list contains active_today, active_past, and snoozed_expired (R-2.5)."""
    result = scan_vault_reminders(vault)
    active_ids = {e["id"] for e in result["active"]}
    assert "active_today" in active_ids, f"active_ids={active_ids}"
    assert "active_past" in active_ids, f"active_ids={active_ids}"
    assert "snoozed_expired" in active_ids, f"active_ids={active_ids}"


def test_approaching_contains_expected_items(vault: Path) -> None:
    """approaching list contains approaching_3d (R-2.6)."""
    result = scan_vault_reminders(vault)
    approaching_ids = {e["id"] for e in result["approaching"]}
    assert "approaching_3d" in approaching_ids, f"approaching_ids={approaching_ids}"


def test_excluded_items_not_in_any_bucket(vault: Path) -> None:
    """no_reminder, far_future, dismissed, snoozed_future, done_with_reminder never appear (R-2.2–R-2.4)."""
    result = scan_vault_reminders(vault)
    all_ids = {e["id"] for e in result["active"]} | {e["id"] for e in result["approaching"]}
    excluded = {"no_reminder", "far_future", "dismissed", "snoozed_future", "done_with_reminder"}
    overlap = all_ids & excluded
    assert not overlap, f"Excluded items appeared in output: {overlap}"


def test_approaching_and_active_are_disjoint(vault: Path) -> None:
    """R-2.7: approaching and active are disjoint."""
    result = scan_vault_reminders(vault)
    active_ids = {e["id"] for e in result["active"]}
    approaching_ids = {e["id"] for e in result["approaching"]}
    overlap = active_ids & approaching_ids
    assert not overlap, f"Items appear in both buckets: {overlap}"


def test_areas_are_scanned(vault: Path) -> None:
    """R-2.1: 03-Areas is scanned, not just 01-Proyectos-Activos."""
    result = scan_vault_reminders(vault)
    active_ids = {e["id"] for e in result["active"]}
    assert "area_active" in active_ids, f"03-Areas item missing; active_ids={active_ids}"


def test_entry_fields(vault: Path) -> None:
    """Each entry has the required fields: id, title, path, reminder_date, proyecto."""
    result = scan_vault_reminders(vault)
    for bucket in ("active", "approaching"):
        for entry in result[bucket]:
            for field in ("id", "title", "path", "reminder_date", "proyecto"):
                assert field in entry, f"Field '{field}' missing in {bucket} entry {entry}"


def test_dismissed_excluded(vault: Path) -> None:
    """R-2.3: files with reminder_dismissed set are excluded."""
    result = scan_vault_reminders(vault)
    all_ids = {e["id"] for e in result["active"]} | {e["id"] for e in result["approaching"]}
    assert "dismissed" not in all_ids


def test_snoozed_future_excluded(vault: Path) -> None:
    """R-2.4: files snoozed until a future date are excluded."""
    result = scan_vault_reminders(vault)
    all_ids = {e["id"] for e in result["active"]} | {e["id"] for e in result["approaching"]}
    assert "snoozed_future" not in all_ids


def test_snoozed_expired_is_active(vault: Path) -> None:
    """R-2.4 + R-2.5: expired snooze means the item is treated as active."""
    result = scan_vault_reminders(vault)
    active_ids = {e["id"] for e in result["active"]}
    assert "snoozed_expired" in active_ids


def test_done_excluded(vault: Path) -> None:
    """R-2.2: estado: done excludes an item even when reminder_date is today."""
    result = scan_vault_reminders(vault)
    all_ids = {e["id"] for e in result["active"]} | {e["id"] for e in result["approaching"]}
    assert "done_with_reminder" not in all_ids


def test_far_future_excluded(vault: Path) -> None:
    """reminder_date > 7 days ahead is not in approaching or active."""
    result = scan_vault_reminders(vault)
    all_ids = {e["id"] for e in result["active"]} | {e["id"] for e in result["approaching"]}
    assert "far_future" not in all_ids


def test_vault_path_in_result(vault: Path) -> None:
    """vault_path field matches the input path."""
    result = scan_vault_reminders(vault)
    assert result["vault_path"] == str(vault)


def test_nonexistent_locations_dont_crash(tmp_path: Path) -> None:
    """An empty vault (no 01-Proyectos-Activos or 03-Areas) returns empty buckets without error."""
    result = scan_vault_reminders(tmp_path)
    assert result["active"] == []
    assert result["approaching"] == []
