#!/usr/bin/env python3
"""
Story 7.1 — verify lib/capture_writer.write_capture.

Acceptance (R-5.4, R-5.5, R-5.6):
  - project_slug=None  -> <vault>/99-Resources/Inbox/UNFILED-NNN.md
  - project_slug="X"   -> <vault>/01-Proyectos-Activos/X/X-CAPTURE-NNN.md
  - numbering increments
  - atomic write (temp file + os.replace)
"""

import os
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from capture_writer import write_capture  # noqa: E402


class TestCaptureWriter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = pathlib.Path(self.tmp.name)
        (self.vault / "01-Proyectos-Activos").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_writes_unfiled_when_no_project(self):
        p = write_capture(self.vault, None, "an idea")
        self.assertTrue(p.is_file())
        self.assertEqual(p.parent.resolve(), (self.vault / "99-Resources" / "Inbox").resolve())
        self.assertTrue(p.name.startswith("UNFILED-"))
        self.assertTrue(p.name.endswith(".md"))
        body = p.read_text(encoding="utf-8")
        self.assertIn("type: capture", body)
        self.assertIn("project: unfiled", body)
        self.assertIn("an idea", body)

    def test_writes_into_project_folder_when_slug_given(self):
        proj = self.vault / "01-Proyectos-Activos" / "PROYECTO-A"
        proj.mkdir()
        p = write_capture(self.vault, "PROYECTO-A", "my project note")
        self.assertEqual(p.parent.resolve(), proj.resolve())
        self.assertTrue(p.name.startswith("PROYECTO-A-CAPTURE-"))
        body = p.read_text(encoding="utf-8")
        self.assertIn("project: PROYECTO-A", body)
        self.assertIn("my project note", body)

    def test_numbering_increments(self):
        p1 = write_capture(self.vault, None, "first")
        p2 = write_capture(self.vault, None, "second")
        p3 = write_capture(self.vault, None, "third")
        nums = sorted(int(p.name.split("-")[-1].rstrip(".md")) for p in (p1, p2, p3))
        self.assertEqual(nums, [1, 2, 3])

    def test_numbering_fills_gaps(self):
        write_capture(self.vault, None, "a")  # 001
        write_capture(self.vault, None, "b")  # 002
        # Remove 001 → next call should reuse 001
        (self.vault / "99-Resources" / "Inbox" / "UNFILED-001.md").unlink()
        p = write_capture(self.vault, None, "c")
        self.assertTrue(p.name.endswith("UNFILED-001.md"))

    def test_atomic_write_leaves_no_tmp_files(self):
        write_capture(self.vault, None, "hi")
        siblings = list((self.vault / "99-Resources" / "Inbox").iterdir())
        self.assertTrue(all(not s.name.endswith(".tmp") for s in siblings))

    def test_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            write_capture(self.vault, None, "")
        with self.assertRaises(ValueError):
            write_capture(self.vault, None, "   \n  ")

    def test_creates_project_folder_if_missing(self):
        # The Inbox path doesn't exist before the first call
        self.assertFalse((self.vault / "99-Resources" / "Inbox").exists())
        write_capture(self.vault, None, "first")
        self.assertTrue((self.vault / "99-Resources" / "Inbox").is_dir())


if __name__ == "__main__":
    unittest.main()
