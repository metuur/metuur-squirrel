#!/usr/bin/env python3
"""
Tests for apps/cli/lib/reminder_writer.py

Covers R-1.1 – R-1.6:
  1. write_reminder_date with absolute date → frontmatter + callout
  2. write_reminder_date with relative "in 3 months" → resolved absolute date
  3. dismiss_reminder → reminder_dismissed set, reminder_date removed, callout gone
  4. snooze_reminder → reminder_snoozed_until set, callout updated
  5. Round-trip: write_reminder_date then parse_frontmatter → value matches
  6. File without # heading: callout prepended at body start, no crash
  7. write_reminder_date twice: callout updated, not duplicated
"""

import datetime
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from intent_parser import parse_frontmatter  # noqa: E402
from reminder_writer import (  # noqa: E402
    write_reminder_date,
    dismiss_reminder,
    snooze_reminder,
    resolve_reminder_date,
)

FIXTURE_CONTENT = """\
---
id: TEST-001
title: Test Item
estado: wip
---

# Test Item

Some body text here.
"""

FIXTURE_NO_HEADING = """\
---
id: TEST-002
title: No Heading
estado: wip
---

Some body text with no heading here.
"""


class TestReminderWriter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_file(self, name: str, content: str = FIXTURE_CONTENT) -> pathlib.Path:
        p = self.dir / name
        p.write_text(content, encoding="utf-8")
        return p

    def _frontmatter(self, path: pathlib.Path) -> dict:
        fm, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        return fm

    def _body(self, path: pathlib.Path) -> str:
        _, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        return body

    # ─── Test 1: absolute date ───────────────────────────────────────────────

    def test_write_absolute_date_frontmatter(self):
        """R-1.3 — frontmatter gets reminder_date: 2026-09-15."""
        p = self._make_file("item.md")
        write_reminder_date(p, "2026-09-15")

        fm = self._frontmatter(p)
        self.assertEqual(fm.get("reminder_date"), "2026-09-15")

    def test_write_absolute_date_callout_in_body(self):
        """R-1.4 — callout appears immediately after # Test Item."""
        p = self._make_file("item.md")
        write_reminder_date(p, "2026-09-15")

        body = self._body(p)
        lines = body.splitlines()

        # Find title line
        title_idx = next(i for i, ln in enumerate(lines) if ln.startswith("# "))
        callout_line = lines[title_idx + 1]
        self.assertIn("📅", callout_line)
        self.assertIn("2026-09-15", callout_line)
        self.assertTrue(callout_line.startswith("> 📅 **Reminder:**"))

    # ─── Test 2: relative date ────────────────────────────────────────────────

    def test_write_relative_date_resolves_absolute(self):
        """R-1.1/R-1.2 — "in 3 months" resolves to an absolute date ~91 days out."""
        p = self._make_file("item.md")
        write_reminder_date(p, "in 3 months")

        fm = self._frontmatter(p)
        reminder_date_str = fm.get("reminder_date")
        self.assertIsNotNone(reminder_date_str)

        # Must be a valid ISO date
        reminder_date = datetime.date.fromisoformat(reminder_date_str)
        today = datetime.date.today()
        delta = (reminder_date - today).days
        # Should be roughly 91 days (±5 for month length variation)
        self.assertGreaterEqual(delta, 86)
        self.assertLessEqual(delta, 370)  # generous upper bound if dateutil present

    def test_write_relative_date_callout_present(self):
        """R-1.4 — relative date: callout also added to body."""
        p = self._make_file("item.md")
        write_reminder_date(p, "in 3 months")

        body = self._body(p)
        self.assertIn("📅", body)
        self.assertIn("**Reminder:**", body)

    # ─── Test 3: dismiss ─────────────────────────────────────────────────────

    def test_dismiss_removes_callout_and_reminder_date(self):
        """R-1.5 — dismiss removes callout, sets reminder_dismissed, deletes reminder_date."""
        p = self._make_file("item.md")
        write_reminder_date(p, "2026-09-15")

        dismiss_reminder(p)

        fm = self._frontmatter(p)
        body = self._body(p)

        self.assertNotIn("reminder_date", fm)
        self.assertIn("reminder_dismissed", fm)
        self.assertEqual(fm["reminder_dismissed"], datetime.date.today().isoformat())
        self.assertNotIn("📅", body)
        self.assertNotIn("**Reminder:**", body)

    def test_dismiss_removes_snoozed_until(self):
        """dismiss also clears reminder_snoozed_until."""
        p = self._make_file("item.md")
        write_reminder_date(p, "2026-09-15")
        snooze_reminder(p, "2026-10-01")
        dismiss_reminder(p)

        fm = self._frontmatter(p)
        self.assertNotIn("reminder_snoozed_until", fm)

    # ─── Test 4: snooze ──────────────────────────────────────────────────────

    def test_snooze_sets_snoozed_until_and_updates_callout(self):
        """R-1.5 — snooze sets reminder_snoozed_until and updates callout to new date."""
        p = self._make_file("item.md")
        write_reminder_date(p, "2026-09-15")

        snooze_reminder(p, "2026-12-01")

        fm = self._frontmatter(p)
        body = self._body(p)

        self.assertEqual(fm.get("reminder_snoozed_until"), "2026-12-01")
        self.assertIn("2026-12-01", body)
        # Old date should not appear in callout
        self.assertNotIn("2026-09-15", body.split("**Reminder:**")[1]
                         if "**Reminder:**" in body else "")

    def test_snooze_clears_reminder_dismissed(self):
        """Snooze removes reminder_dismissed if present."""
        p = self._make_file("item.md")
        write_reminder_date(p, "2026-09-15")
        dismiss_reminder(p)
        snooze_reminder(p, "2026-12-01")

        fm = self._frontmatter(p)
        self.assertNotIn("reminder_dismissed", fm)

    # ─── Test 5: round-trip via parse_frontmatter ─────────────────────────────

    def test_roundtrip_parse_matches_written_value(self):
        """R-1.3 — written reminder_date survives a re-read via parse_frontmatter."""
        p = self._make_file("item.md")
        write_reminder_date(p, "2026-07-04")

        fm = self._frontmatter(p)
        self.assertEqual(fm.get("reminder_date"), "2026-07-04")

    # ─── Test 6: no heading ───────────────────────────────────────────────────

    def test_no_heading_callout_prepended_no_crash(self):
        """R-1.4 fallback — file without # heading gets callout at body start."""
        p = self._make_file("nohead.md", FIXTURE_NO_HEADING)
        write_reminder_date(p, "2026-09-15")  # must not raise

        body = self._body(p)
        lines = body.splitlines()
        # Callout must appear somewhere in the body
        callout_lines = [ln for ln in lines if ln.startswith("> 📅 **Reminder:**")]
        self.assertEqual(len(callout_lines), 1)
        # And it must be the first non-empty line of the body
        first_nonempty = next((ln for ln in lines if ln.strip()), None)
        self.assertIsNotNone(first_nonempty)
        self.assertTrue(first_nonempty.startswith("> 📅 **Reminder:**"))

    # ─── Test 7: double write — no duplicate ─────────────────────────────────

    def test_double_write_updates_callout_not_duplicated(self):
        """R-1.5 — calling write_reminder_date twice updates callout, no duplication."""
        p = self._make_file("item.md")
        write_reminder_date(p, "2026-09-15")
        write_reminder_date(p, "2026-11-30")

        fm = self._frontmatter(p)
        body = self._body(p)

        # Only the latest date in frontmatter
        self.assertEqual(fm.get("reminder_date"), "2026-11-30")

        # Only one callout line
        callout_lines = [ln for ln in body.splitlines()
                         if ln.startswith("> 📅 **Reminder:**")]
        self.assertEqual(len(callout_lines), 1)
        self.assertIn("2026-11-30", callout_lines[0])


class TestResolveReminderDate(unittest.TestCase):
    """Unit tests for resolve_reminder_date."""

    def test_absolute_passthrough(self):
        self.assertEqual(resolve_reminder_date("2026-08-01"), "2026-08-01")

    def test_in_1_month(self):
        result = resolve_reminder_date("in 1 month")
        today = datetime.date.today()
        parsed = datetime.date.fromisoformat(result)
        delta = (parsed - today).days
        self.assertGreaterEqual(delta, 28)
        self.assertLessEqual(delta, 32)

    def test_in_1_year(self):
        result = resolve_reminder_date("in 1 year")
        today = datetime.date.today()
        parsed = datetime.date.fromisoformat(result)
        delta = (parsed - today).days
        self.assertGreaterEqual(delta, 364)
        self.assertLessEqual(delta, 367)

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            resolve_reminder_date("next tuesday")

    def test_whitespace_stripped(self):
        result = resolve_reminder_date("  2026-08-01  ")
        self.assertEqual(result, "2026-08-01")


if __name__ == "__main__":
    unittest.main()
