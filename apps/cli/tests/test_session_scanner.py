"""Unit tests for session_scanner.py — Copilot session-state fallback (8.1)."""

import datetime
import json
import os
import pathlib
import sys
import tempfile
import unittest

# Add lib/ to sys.path
_LIB = pathlib.Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(_LIB))

from session_scanner import _parse_copilot_jsonl_row, _read_copilot_jsonl_sessions


class TestParseCopilotJsonlRow(unittest.TestCase):
    def test_valid_row_with_file(self):
        row = json.dumps({"file": "/tmp/foo.py", "project": "MY-PROJECT"})
        result = _parse_copilot_jsonl_row(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["file"], "/tmp/foo.py")
        self.assertEqual(result["project"], "MY-PROJECT")

    def test_valid_row_with_file_path_key(self):
        row = json.dumps({"filePath": "/tmp/bar.ts"})
        result = _parse_copilot_jsonl_row(row)
        self.assertIsNotNone(result)
        self.assertEqual(result["file"], "/tmp/bar.ts")

    def test_malformed_row_skipped(self):
        result = _parse_copilot_jsonl_row("not json {{{")
        self.assertIsNone(result)

    def test_empty_row_skipped(self):
        self.assertIsNone(_parse_copilot_jsonl_row(""))
        self.assertIsNone(_parse_copilot_jsonl_row("   "))

    def test_row_with_no_useful_fields_skipped(self):
        row = json.dumps({"timestamp": "2026-01-01T00:00:00Z", "type": "unknown"})
        self.assertIsNone(_parse_copilot_jsonl_row(row))

    def test_no_exception_on_unknown_schema(self):
        row = json.dumps({"some_random_key": [1, 2, 3], "nested": {"deep": True}})
        # Must not raise; returns None (no useful fields)
        result = _parse_copilot_jsonl_row(row)
        self.assertIsNone(result)


class TestReadCopilotJsonlSessions(unittest.TestCase):
    def _write_session_file(self, directory: pathlib.Path, name: str, rows: list) -> pathlib.Path:
        f = directory / name
        f.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return f

    def test_valid_row_contributes_file_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = pathlib.Path(tmpdir) / "session-state"
            session_dir.mkdir()
            self._write_session_file(session_dir, "abc123.jsonl", [
                {"file": "/home/user/project/main.py", "project": "PROJ-A"},
                "this is not json",
                {"unknown_field": "ignored"},
            ])
            cutoff = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=72)

            old_env = os.environ.get("COPILOT_HOME")
            os.environ["COPILOT_HOME"] = tmpdir
            try:
                sessions = _read_copilot_jsonl_sessions(cutoff)
            finally:
                if old_env is None:
                    os.environ.pop("COPILOT_HOME", None)
                else:
                    os.environ["COPILOT_HOME"] = old_env

        self.assertEqual(len(sessions), 1)
        sess = sessions[0]
        self.assertIn("/home/user/project/main.py", sess["files_edited"])
        self.assertEqual(sess["source"], "copilot_jsonl")

    def test_missing_directory_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # No session-state/ subdir created
            cutoff = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=72)
            old_env = os.environ.get("COPILOT_HOME")
            os.environ["COPILOT_HOME"] = tmpdir
            try:
                sessions = _read_copilot_jsonl_sessions(cutoff)
            finally:
                if old_env is None:
                    os.environ.pop("COPILOT_HOME", None)
                else:
                    os.environ["COPILOT_HOME"] = old_env
        self.assertEqual(sessions, [])

    def test_all_malformed_rows_no_exception(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = pathlib.Path(tmpdir) / "session-state"
            session_dir.mkdir()
            self._write_session_file(session_dir, "bad.jsonl", [])
            (session_dir / "bad.jsonl").write_text("not json\nalso not json\n", encoding="utf-8")

            cutoff = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=72)
            old_env = os.environ.get("COPILOT_HOME")
            os.environ["COPILOT_HOME"] = tmpdir
            try:
                sessions = _read_copilot_jsonl_sessions(cutoff)
            finally:
                if old_env is None:
                    os.environ.pop("COPILOT_HOME", None)
                else:
                    os.environ["COPILOT_HOME"] = old_env
        # File with only malformed rows produces no sessions (line_count == 0)
        self.assertEqual(sessions, [])


if __name__ == "__main__":
    unittest.main()
