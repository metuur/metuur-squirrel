"""Tests for post_it_layout table in SQLite schema (task 1.1)."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from db import init_schema  # noqa: E402


def test_init_schema_idempotent():
    """Calling init_schema twice on a fresh in-memory DB raises no error."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    init_schema(conn)  # second call must not raise
    conn.close()


def test_post_it_layout_table_exists_with_expected_columns():
    """post_it_layout table exists with the required columns after init_schema."""
    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    # Confirm the table exists
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='post_it_layout'"
    ).fetchone()
    assert row is not None, "post_it_layout table not found in sqlite_master"

    # Collect column names via PRAGMA
    cols = {r[1] for r in conn.execute("PRAGMA table_info(post_it_layout)")}
    expected = {"vault", "post_it_id", "x", "y", "rotation", "z", "updated_at"}
    assert expected == cols, f"Column mismatch. Got: {cols}"

    conn.close()
