#!/usr/bin/env python3
"""
Mind Journal & 4-Hour Mood Check-In — lib/mind_journal tests.

Acceptance:
  R-1.1–R-1.6, R-1.8 — Seeding once per vault via the mind_journal_seeded flag.
  R-2.1              — Discovery by `journal: true` marker, not filename.
  R-2.2–R-2.8        — Interval / waking-window due computation, request-time.
  R-3.4, R-3.5, R-3.6, R-3.11 — Entry append, mood tagging, clock reset, order.
  R-3.8, R-3.9       — Config upsert.
"""

import datetime
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

import config_loader  # noqa: E402
import mind_journal  # noqa: E402
from mind_journal import (  # noqa: E402
    DEFAULT_INTERVAL_HOURS,
    JOURNAL_ID,
    append_entry,
    compute_due,
    ensure_mind_journal,
    find_journal,
    parse_entries,
    read_journal,
    write_config,
)

TZ = datetime.datetime.now().astimezone().tzinfo


def _dt(y, mo, d, h, mi=0):
    return datetime.datetime(y, mo, d, h, mi, tzinfo=TZ)


class _VaultTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = pathlib.Path(self._tmp.name) / "vault"
        (self.vault / "01-Active-Projects" / "SCRATCH-PAD").mkdir(parents=True)
        # Isolate per-vault state JSON into the temp dir.
        self.state_dir = pathlib.Path(self._tmp.name) / "state"
        self._orig_state_dir = config_loader.DEFAULT_STATE_DIR
        config_loader.DEFAULT_STATE_DIR = self.state_dir
        self.vault_name = "testvault"

    def tearDown(self):
        config_loader.DEFAULT_STATE_DIR = self._orig_state_dir
        self._tmp.cleanup()

    def _journal_path(self):
        return self.vault / "01-Active-Projects" / "SCRATCH-PAD" / f"{JOURNAL_ID}.md"


# ── Unit 1: Seeding ────────────────────────────────────────────────────────────

class SeedingTests(_VaultTest):
    def test_seeds_journal_and_sets_flag(self):  # R-1.2, R-1.4
        ensure_mind_journal(self.vault, self.vault_name)
        jp = self._journal_path()
        self.assertTrue(jp.exists())
        text = jp.read_text(encoding="utf-8")
        self.assertIn("journal: true", text)
        self.assertIn(f"reminder_interval_hours: {DEFAULT_INTERVAL_HOURS}", text)
        self.assertIn('waking_start: "08:00"', text)
        self.assertIn("## Entries", text)
        self.assertIn("delete it anytime", text)  # R-1.3
        self.assertNotIn("protected:", text)  # R-1.6
        self.assertTrue(config_loader.read_state(self.vault_name).get("mind_journal_seeded"))

    def test_second_call_is_noop(self):  # R-1.5
        ensure_mind_journal(self.vault, self.vault_name)
        ensure_mind_journal(self.vault, self.vault_name)
        self.assertTrue(self._journal_path().exists())

    def test_deleted_journal_not_recreated(self):  # R-1.5
        ensure_mind_journal(self.vault, self.vault_name)
        self._journal_path().unlink()
        ensure_mind_journal(self.vault, self.vault_name)
        self.assertFalse(self._journal_path().exists())

    def test_failure_is_non_fatal(self):  # R-1.8
        # Point at a path that cannot be created (a file where a dir must go).
        bogus = pathlib.Path(self._tmp.name) / "afile"
        bogus.write_text("x")
        # Should swallow the error and not raise.
        ensure_mind_journal(bogus, self.vault_name)


# ── Unit 2: Discovery & due computation ────────────────────────────────────────

class DiscoveryTests(_VaultTest):
    def test_found_by_marker_not_filename(self):  # R-2.1
        ensure_mind_journal(self.vault, self.vault_name)
        original = self._journal_path()
        renamed = original.with_name("RENAMED-JOURNAL.md")
        original.rename(renamed)
        self.assertEqual(find_journal(self.vault), renamed)

    def test_none_when_no_marker(self):
        self.assertIsNone(find_journal(self.vault))

    def test_excluded_from_reminder_buckets(self):  # R-4.5
        import reminder_scanner
        ensure_mind_journal(self.vault, self.vault_name)
        data = reminder_scanner.scan_vault_reminders(self.vault)
        ids = {e["id"] for e in data.get("approaching", []) + data.get("active", [])}
        self.assertNotIn(JOURNAL_ID, ids)


class DueComputationTests(unittest.TestCase):
    def _fm(self, **kw):
        fm = {
            "reminder_interval_hours": 4,
            "reminder_last_logged": _dt(2026, 6, 3, 10, 0).isoformat(),
            "waking_start": "08:00",
            "waking_end": "22:00",
        }
        fm.update(kw)
        return fm

    def test_not_due_before_boundary(self):  # R-2.5
        out = compute_due(self._fm(), now=_dt(2026, 6, 3, 13, 0))
        self.assertFalse(out["due"])

    def test_due_at_boundary_in_window(self):  # R-2.5
        out = compute_due(self._fm(), now=_dt(2026, 6, 3, 14, 0))
        self.assertTrue(out["due"])

    def test_not_due_outside_window(self):  # R-2.6
        # last=00:00, interval 4 -> boundary 04:00 (outside window). now 05:00 outside.
        fm = self._fm(reminder_last_logged=_dt(2026, 6, 3, 0, 0).isoformat())
        out = compute_due(fm, now=_dt(2026, 6, 3, 5, 0))
        self.assertFalse(out["due"])

    def test_next_due_defers_to_waking_start(self):  # R-2.7
        fm = self._fm(reminder_last_logged=_dt(2026, 6, 2, 23, 0).isoformat())
        # boundary = 03:00 (outside window) -> next_due should be 08:00 same day.
        out = compute_due(fm, now=_dt(2026, 6, 3, 1, 0))
        self.assertEqual(out["next_due"][11:16], "08:00")
        self.assertTrue(out["next_due"].startswith("2026-06-03"))

    def test_defaults_when_fields_missing(self):  # R-2.2, R-2.4
        out = compute_due({"created": "2026-06-03"}, now=_dt(2026, 6, 3, 9, 0))
        self.assertEqual(out["interval_hours"], float(DEFAULT_INTERVAL_HOURS))
        self.assertEqual(out["waking"], {"start": "08:00", "end": "22:00"})

    def test_bad_interval_falls_back(self):  # R-2.2
        out = compute_due(self._fm(reminder_interval_hours="oops"),
                          now=_dt(2026, 6, 3, 14, 0))
        self.assertEqual(out["interval_hours"], float(DEFAULT_INTERVAL_HOURS))


# ── Unit 3: Entry append / parse / config ──────────────────────────────────────

class EntryTests(_VaultTest):
    def setUp(self):
        super().setUp()
        ensure_mind_journal(self.vault, self.vault_name)
        self.jp = self._journal_path()

    def test_append_and_parse(self):  # R-3.5, R-3.11
        append_entry(self.jp, "clear and focused", "writing tests", "happy",
                     now=_dt(2026, 6, 3, 14, 0))
        append_entry(self.jp, "a bit tired", "debugging", "sad",
                     now=_dt(2026, 6, 3, 18, 0))
        entries = parse_entries(self.jp.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["mood"], "happy")
        self.assertEqual(entries[0]["mind"], "clear and focused")
        self.assertEqual(entries[0]["doing"], "writing tests")
        self.assertEqual(entries[1]["mood"], "sad")  # chronological order

    def test_append_resets_clock(self):  # R-3.6
        append_entry(self.jp, "x", "y", "neutral", now=_dt(2026, 6, 3, 14, 0))
        out = read_journal(self.vault, now=_dt(2026, 6, 3, 15, 0))
        self.assertFalse(out["due"])  # boundary now 18:00
        out2 = read_journal(self.vault, now=_dt(2026, 6, 3, 18, 30))
        self.assertTrue(out2["due"])

    def test_write_config(self):  # R-3.8
        write_config(self.jp, interval_hours=6, waking_start="07:00")
        text = self.jp.read_text(encoding="utf-8")
        self.assertIn("reminder_interval_hours: 6", text)
        self.assertIn('waking_start: "07:00"', text)

    def test_read_journal_shape(self):  # R-3.1
        out = read_journal(self.vault, now=_dt(2026, 6, 3, 9, 0))
        self.assertTrue(out["exists"])
        self.assertEqual(out["task"]["id"], JOURNAL_ID)
        self.assertIn("due", out)
        self.assertIn("next_due", out)
        self.assertIn("waking", out)

    def test_read_journal_absent(self):  # R-3.2
        self.jp.unlink()
        self.assertEqual(read_journal(self.vault), {"exists": False})


if __name__ == "__main__":
    unittest.main()
