#!/usr/bin/env python3
"""
Tests for post_it_writer.py — Task 1.2 acceptance criteria.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

import pytest
from post_it_writer import (
    create,
    update,
    archive,
    restore,
    delete,
    record_conversion,
    resolve_post_it_path,
    POST_ITS_DIR,
)
from intent_parser import parse_intent


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def vault(tmp_path):
    """A temporary vault directory."""
    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_create_sequential_ids(vault):
    """R-1.1: create writes PI-001, PI-002, PI-003 in sequence."""
    id1 = create(vault, "first note")
    id2 = create(vault, "second note")
    id3 = create(vault, "third note")

    assert id1 == "PI-001"
    assert id2 == "PI-002"
    assert id3 == "PI-003"

    folder = vault / POST_ITS_DIR
    assert (folder / "PI-001.md").exists()
    assert (folder / "PI-002.md").exists()
    assert (folder / "PI-003.md").exists()


def test_frontmatter_keys(vault):
    """R-1.2 / R-1.3: required keys present; forbidden keys absent."""
    pi_id = create(vault, "remember this")

    path = resolve_post_it_path(vault, pi_id)
    fm = parse_intent(path)["frontmatter"]

    required = {"id", "type", "state", "color", "label", "pinned", "created", "converted_to"}
    for key in required:
        assert key in fm, f"expected frontmatter key '{key}' not found"

    forbidden = {"status", "reminder_date", "due"}
    for key in forbidden:
        assert key not in fm, f"forbidden frontmatter key '{key}' found"

    assert fm["type"] == "post_it"
    assert fm["state"] == "active"
    assert fm["id"] == "PI-001"


def test_update_fields(vault):
    """update() correctly mutates color and label in the frontmatter."""
    pi_id = create(vault, "original text")

    update(vault, pi_id, {"color": "blue", "label": "idea"})

    path = resolve_post_it_path(vault, pi_id)
    fm = parse_intent(path)["frontmatter"]
    assert fm["color"] == "blue"
    assert fm["label"] == "idea"


def test_archive_restore(vault):
    """archive() sets state=archived; restore() sets state=active."""
    pi_id = create(vault, "sticky note")

    archive(vault, pi_id)
    path = resolve_post_it_path(vault, pi_id)
    fm = parse_intent(path)["frontmatter"]
    assert fm["state"] == "archived"

    restore(vault, pi_id)
    fm = parse_intent(path)["frontmatter"]
    assert fm["state"] == "active"


def test_delete(vault):
    """delete() removes the file."""
    pi_id = create(vault, "to be deleted")
    path = resolve_post_it_path(vault, pi_id)
    assert path is not None and path.exists()

    delete(vault, pi_id)
    assert not path.exists()


def test_record_conversion(vault):
    """record_conversion() sets state=archived and converted_to=ref."""
    pi_id = create(vault, "convert me")

    record_conversion(vault, pi_id, "quick_task:QT-001")

    path = resolve_post_it_path(vault, pi_id)
    fm = parse_intent(path)["frontmatter"]
    assert fm["state"] == "archived"
    assert fm["converted_to"] == "quick_task:QT-001"
