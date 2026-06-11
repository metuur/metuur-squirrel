"""
test_post_it_scanner.py — Tests for post_it_scanner.scan_post_its.

Covers R-2.1 (ordering):
  - pinned items appear before unpinned in the active list
  - within each group items are newest-first by `created`
  - archived items are in their own list, newest-first
  - files with broken YAML degrade gracefully (skip, no exception)
  - result items carry the full expected field set
"""

import datetime
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from post_it_scanner import scan_post_its
from post_it_writer import create, archive, update


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _vault(tmp_path: Path) -> Path:
    """Return a vault root with the 05-Post-its folder pre-created."""
    (tmp_path / "05-Post-its").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _write_bad_file(vault: Path, name: str, content: str) -> Path:
    """Write a raw markdown file directly into 05-Post-its/."""
    p = vault / "05-Post-its" / name
    p.write_text(content, encoding="utf-8")
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_ordering_pinned_first(tmp_path):
    """Active list: pinned item sorts before unpinned, unpinned newest-first."""
    vault = _vault(tmp_path)
    now = datetime.datetime.now().astimezone()

    # Create older-unpinned first so its ID is PI-001.
    older_id = create(vault, "older unpinned", color="yellow")
    # Brief sleep substitute: write a slightly-future created via update is
    # awkward, so instead we overwrite the file directly with later timestamps.
    # Easier: just create them in order and rely on sub-second differences being
    # enough.  To guarantee ordering, rewrite the frontmatter timestamps.
    import time
    time.sleep(0.05)
    newer_id = create(vault, "newer unpinned", color="blue")
    time.sleep(0.05)
    pinned_id = create(vault, "pinned note", color="green")
    update(vault, pinned_id, {"pinned": True})

    result = scan_post_its(vault)
    active = result["active"]

    assert len(active) == 3
    assert active[0]["id"] == pinned_id, "pinned item must be first"
    assert active[1]["id"] == newer_id, "newer unpinned must be second"
    assert active[2]["id"] == older_id, "older unpinned must be last"


def test_archived_separate(tmp_path):
    """Archived post-it goes to archived list; active stays in active."""
    vault = _vault(tmp_path)

    active_id = create(vault, "active note")
    archived_id = create(vault, "archived note")
    archive(vault, archived_id)

    result = scan_post_its(vault)

    active_ids = [e["id"] for e in result["active"]]
    archived_ids = [e["id"] for e in result["archived"]]

    assert active_id in active_ids
    assert archived_id not in active_ids
    assert archived_id in archived_ids
    assert active_id not in archived_ids

    assert len(result["active"]) == 1
    assert len(result["archived"]) == 1


def test_graceful_on_mangled_frontmatter(tmp_path):
    """A file that raises on read is skipped gracefully; valid files are returned."""
    vault = _vault(tmp_path)

    pi1 = create(vault, "note one")
    pi2 = create(vault, "note two")

    # Write invalid UTF-8 bytes to trigger a decode error on read_text.
    bad_path = vault / "05-Post-its" / "PI-BAD.md"
    bad_path.write_bytes(b"---\nid: PI-BAD\ntype: post_it\n---\n\xc3\x28invalid utf8\n")

    result = scan_post_its(vault)

    # The two valid notes must be present; the bad file must not raise.
    ids = [e["id"] for e in result["active"]]
    assert pi1 in ids
    assert pi2 in ids
    # Total active count is exactly 2 (bad file skipped).
    assert len(result["active"]) == 2


def test_fields_present(tmp_path):
    """Scanned item carries all required fields."""
    vault = _vault(tmp_path)

    pi_id = create(vault, "my note text", color="pink", label="work")

    result = scan_post_its(vault)
    assert len(result["active"]) == 1

    item = result["active"][0]
    required_fields = {"id", "text", "color", "label", "pinned", "state", "created", "converted_to", "path"}
    assert required_fields.issubset(item.keys()), (
        f"Missing fields: {required_fields - item.keys()}"
    )

    assert item["id"] == pi_id
    assert item["text"] == "my note text"
    assert item["color"] == "pink"
    assert item["label"] == "work"
    assert item["pinned"] is False
    assert item["state"] == "active"
    assert item["created"] != ""
    assert item["converted_to"] == ""
    assert item["path"].endswith(f"{pi_id}.md")


def test_empty_vault_is_safe(tmp_path):
    """No 05-Post-its folder → empty result, no error."""
    result = scan_post_its(tmp_path)
    assert result["active"] == []
    assert result["archived"] == []
    assert "scanned_at" in result


def test_non_post_it_files_ignored(tmp_path):
    """Files without type: post_it in frontmatter are silently skipped."""
    vault = _vault(tmp_path)

    _write_bad_file(
        vault,
        "NOTE-001.md",
        "---\nid: NOTE-001\ntype: note\nstate: active\n---\n\nsome note\n",
    )

    result = scan_post_its(vault)
    assert result["active"] == []
    assert result["archived"] == []


def test_archived_newest_first(tmp_path):
    """Archived list is sorted newest-first by created."""
    import time
    vault = _vault(tmp_path)

    old_id = create(vault, "old archived")
    time.sleep(0.05)
    new_id = create(vault, "new archived")

    archive(vault, old_id)
    archive(vault, new_id)

    result = scan_post_its(vault)
    archived_ids = [e["id"] for e in result["archived"]]

    assert archived_ids[0] == new_id, "newest archived must be first"
    assert archived_ids[1] == old_id
