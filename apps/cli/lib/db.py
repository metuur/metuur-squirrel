#!/usr/bin/env python3
"""
db.py — SQLite connection and schema initialisation for Squirrel.

Public API:
    get_conn(state_dir=None) -> sqlite3.Connection
    init_schema(conn) -> None
"""

import pathlib
import sqlite3

from config_loader import DEFAULT_STATE_DIR


def get_conn(state_dir=None) -> sqlite3.Connection:
    """Open and return a new sqlite3.Connection to squirrel.db.

    Each call returns an independent connection (no shared global).
    WAL mode is enabled on every connection.

    Args:
        state_dir: Directory containing squirrel.db. Defaults to
                   DEFAULT_STATE_DIR (~/.squirrel/state).
    """
    if state_dir is None:
        state_dir = DEFAULT_STATE_DIR
    state_dir = pathlib.Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    db_path = state_dir / "squirrel.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create focus_picks and work_sessions tables if they do not exist.

    Idempotent — safe to call multiple times on the same database.
    """
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS focus_picks (
          id            INTEGER PRIMARY KEY,
          vault         TEXT NOT NULL,
          slot          TEXT NOT NULL,
          date          TEXT NOT NULL,
          project_slug  TEXT NOT NULL,
          intent_slug   TEXT NOT NULL,
          picked_at     TEXT NOT NULL,
          cleared_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS work_sessions (
          id            INTEGER PRIMARY KEY,
          vault         TEXT NOT NULL,
          slot          TEXT NOT NULL,
          date          TEXT NOT NULL,
          project_slug  TEXT NOT NULL,
          intent_slug   TEXT NOT NULL,
          checkin_at    TEXT NOT NULL,
          checkout_at   TEXT
        );
    """)
    conn.commit()
