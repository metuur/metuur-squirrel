#!/usr/bin/env python3
"""
Tests for the four v0.2 shippable units.
Run: python3 -m unittest tests.test_v02_units
"""

import datetime
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from manifest_writer import _read_vault_path, main as manifest_writer_main
from session_scanner import (
    _read_manifest,
    _group_manifest_entries,
    _filter_by_environment,
    scan_sessions,
)


# ─── manifest_writer tests ────────────────────────────────────────────────────

class TestManifestWriter(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.vault = self.tmpdir / "vault"
        self.vault.mkdir()
        self.config_dir = self.tmpdir / ".squirrel"
        self.config_dir.mkdir()
        self.config_file = self.config_dir / "config.toml"

    def _write_config(self, vault_path: str) -> None:
        self.config_file.write_text(f'vault_path = "{vault_path}"\n')

    def test_manifest_written_on_edit(self):
        self._write_config(str(self.vault))
        manifest = self.vault / ".squirrel" / "session-manifest.jsonl"

        env = {
            "TOOL_INPUT": json.dumps({"file_path": "/tmp/foo.py"}),
            "CWD": "/tmp",
            "CLAUDE_SESSION_ID": "test-session-123",
        }
        with patch.dict(os.environ, env), \
             patch("pathlib.Path.expanduser", side_effect=lambda p: p):
            # Write config at the path manifest_writer reads
            orig = Path("~/.squirrel/config.toml")
            # Patch _read_vault_path directly
            with patch("manifest_writer._read_vault_path", return_value=self.vault):
                manifest_writer_main()

        self.assertTrue(manifest.exists())
        line = json.loads(manifest.read_text().strip())
        self.assertEqual(line["file"], "/tmp/foo.py")
        self.assertEqual(line["event"], "PostToolUse:Edit")
        self.assertEqual(line["session"], "test-session-123")

    def test_manifest_appends_multiple_entries(self):
        manifest = self.vault / ".squirrel" / "session-manifest.jsonl"
        manifest.parent.mkdir(parents=True, exist_ok=True)

        for fp in ["/a.py", "/b.py", "/c.py"]:
            env = {"TOOL_INPUT": json.dumps({"file_path": fp}), "CWD": "/", "CLAUDE_SESSION_ID": "s1"}
            with patch.dict(os.environ, env), \
                 patch("manifest_writer._read_vault_path", return_value=self.vault):
                manifest_writer_main()

        lines = [json.loads(l) for l in manifest.read_text().strip().splitlines()]
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0]["file"], "/a.py")
        self.assertEqual(lines[2]["file"], "/c.py")

    def test_no_config_exits_cleanly(self):
        with patch("manifest_writer._read_vault_path", return_value=None):
            manifest_writer_main()  # must not raise


# ─── session_scanner tests ────────────────────────────────────────────────────

class TestSessionScanner(unittest.TestCase):

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.vault = self.tmpdir / "vault"
        (self.vault / ".squirrel").mkdir(parents=True)

    def _write_manifest(self, entries: list[dict]) -> None:
        manifest = self.vault / ".squirrel" / "session-manifest.jsonl"
        with open(manifest, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def _make_entry(self, **kwargs) -> dict:
        defaults = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "cwd": "/Users/test/myproject",
            "file": "/Users/test/myproject/foo.py",
            "event": "PostToolUse:Edit",
            "session": "sess-1",
        }
        defaults.update(kwargs)
        return defaults

    # R-4.1 primary source
    def test_reads_manifest_when_present(self):
        self._write_manifest([self._make_entry()])
        sessions = scan_sessions(self.vault, max_age_hours=72, config={})
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["source"], "manifest")

    # R-4.1 age filter
    def test_filters_old_sessions(self):
        old_ts = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=73)).isoformat() + "Z"
        recent_ts = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        self._write_manifest([
            self._make_entry(timestamp=old_ts, session="old"),
            self._make_entry(timestamp=recent_ts, session="new"),
        ])
        sessions = scan_sessions(self.vault, max_age_hours=72, config={})
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "new")

    # R-4.1 grouping by session_id
    def test_groups_entries_by_session(self):
        self._write_manifest([
            self._make_entry(session="s1", file="/a.py"),
            self._make_entry(session="s1", file="/b.py"),
            self._make_entry(session="s2", file="/c.py"),
        ])
        sessions = scan_sessions(self.vault, max_age_hours=72, config={})
        self.assertEqual(len(sessions), 2)
        s1 = next(s for s in sessions if s["session_id"] == "s1")
        self.assertEqual(len(s1["files_edited"]), 2)

    # R-4.2 compliance filter — strict mode blocks corporate cwd
    def test_compliance_filter_excludes_corporate_cwd(self):
        self._write_manifest([
            self._make_entry(session="personal", cwd="/Users/test/personal"),
            self._make_entry(session="work", cwd="/Users/test/corp-internal"),
        ])
        config = {
            "compliance": {
                "strict": "true",
                "corporate_domains": '["corp-internal"]',
            }
        }
        sessions = scan_sessions(self.vault, max_age_hours=72, config=config)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "personal")

    # R-4.2 non-strict mode passes everything through
    def test_no_filter_when_not_strict(self):
        self._write_manifest([
            self._make_entry(session="personal", cwd="/Users/test/personal"),
            self._make_entry(session="work", cwd="/Users/test/corp-internal"),
        ])
        config = {
            "compliance": {
                "strict": "false",
                "corporate_domains": '["corp-internal"]',
            }
        }
        sessions = scan_sessions(self.vault, max_age_hours=72, config=config)
        self.assertEqual(len(sessions), 2)

    # R-4.1 fallback: empty manifest yields no crash (JSONL fallback may or may not find sessions)
    def test_empty_manifest_does_not_crash(self):
        # No manifest file at all
        sessions = scan_sessions(self.vault, max_age_hours=72, config={})
        # May find claude JSONL sessions or return empty — must not raise
        self.assertIsInstance(sessions, list)

    # Sorted descending by last_seen
    def test_sessions_sorted_by_recency(self):
        older = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=1)).isoformat() + "Z"
        newer = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        self._write_manifest([
            self._make_entry(session="old", timestamp=older),
            self._make_entry(session="new", timestamp=newer),
        ])
        sessions = scan_sessions(self.vault, max_age_hours=72, config={})
        self.assertEqual(sessions[0]["session_id"], "new")


if __name__ == "__main__":
    unittest.main(verbosity=2)
