#!/usr/bin/env python3
"""
Tests para los scripts foundation del plugin.
Run: python3 -m unittest tests.test_foundation
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from intent_parser import (
    parse_intent,
    parse_frontmatter,
    parse_sections,
    parse_checkboxes,
    parse_shutdown_notes,
)
from estimate_buffer import adjust_estimate, get_multiplier, parse_estimate
from chunk_helper import chunk_task
from switch_tracker import record_switch, get_status, compute_focus_score
from deadline_scanner import classify_urgency, URGENCY_LEVELS


FIXTURES = Path(__file__).parent / "fixtures" / "vault-minimal"


class TestIntentParser(unittest.TestCase):

    def test_parse_simple_frontmatter(self):
        content = """---
id: TEST-001
status: in-progress
---
# Body"""
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm["id"], "TEST-001")
        self.assertEqual(fm["status"], "in-progress")
        self.assertIn("# Body", body)

    def test_parse_inline_list(self):
        content = """---
tags: [intent, project/X, status/wip]
---
"""
        fm, _ = parse_frontmatter(content)
        self.assertEqual(fm["tags"], ["intent", "project/X", "status/wip"])

    def test_parse_block_list(self):
        content = """---
stakeholders:
  - lead
  - PM
  - architect
---
"""
        fm, _ = parse_frontmatter(content)
        self.assertEqual(fm["stakeholders"], ["lead", "PM", "architect"])

    def test_no_frontmatter(self):
        content = "# Just a title\n\nSome content"
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm, {})
        self.assertEqual(body, content)

    def test_parse_checkboxes(self):
        text = """- [x] Done item 1
- [ ] Pending item
- [X] Done item 2 (uppercase)
- [ ] Another pending"""
        done, pending = parse_checkboxes(text)
        self.assertEqual(len(done), 2)
        self.assertEqual(len(pending), 2)
        self.assertEqual(done[0], "Done item 1")

    def test_parse_sections_with_emoji(self):
        body = """## 🎯 Objetivo
Goal text

## ✅ Definition of Done
- [x] criteria

## 📝 Notas
Notes here"""
        sections = parse_sections(body)
        self.assertIn("objective", sections)
        self.assertIn("definition_of_done", sections)
        self.assertIn("notes", sections)
        self.assertEqual(sections["objective"], "Goal text")

    def test_parse_shutdown_notes(self):
        text = """### 2026-05-22 17:30
- **State**: working state
- **Next physical action**: open file X
- **Hypothesis**: maybe Y
- **Blocked by**: nothing

### 2026-05-20 10:00
- **State**: earlier state
- **Next**: do Z"""
        notes = parse_shutdown_notes(text)
        self.assertEqual(len(notes), 2)
        self.assertEqual(notes[0]["timestamp"], "2026-05-22 17:30")
        self.assertEqual(notes[0]["state"], "working state")
        self.assertEqual(notes[0]["next_action"], "open file X")
        self.assertEqual(notes[0]["hypothesis"], "maybe Y")
        self.assertEqual(notes[1]["timestamp"], "2026-05-20 10:00")

    def test_parse_full_intent(self):
        path = FIXTURES / "01-Active-Projects" / "TEST-PROJECT" / "TEST-PROJECT-AUTH-002.md"
        data = parse_intent(path)
        self.assertEqual(data["id"], "TEST-PROJECT-AUTH-002")
        self.assertEqual(data["frontmatter"]["status"], "in-progress")
        self.assertEqual(data["stats"]["definition_of_done"]["done_count"], 2)
        self.assertEqual(data["stats"]["definition_of_done"]["total"], 6)
        self.assertEqual(data["stats"]["definition_of_done"]["percent_done"], 33)
        self.assertEqual(len(data["shutdown_notes"]), 2)
        self.assertIn("auth.controller.ts", data["shutdown_notes"][0]["next_action"])


class TestEstimateBuffer(unittest.TestCase):

    def test_multiplier_short_task(self):
        self.assertEqual(get_multiplier(5), 3.0)
        self.assertEqual(get_multiplier(30), 3.0)

    def test_multiplier_medium_task(self):
        self.assertEqual(get_multiplier(60), 2.5)

    def test_multiplier_long_task(self):
        self.assertEqual(get_multiplier(120), 2.0)
        self.assertEqual(get_multiplier(480), 2.0)

    def test_multiplier_very_long(self):
        self.assertEqual(get_multiplier(960), 1.5)

    def test_adjust_30min(self):
        result = adjust_estimate(30)
        self.assertEqual(result["user_estimate_minutes"], 30)
        self.assertEqual(result["adjusted_minutes"], 90)
        self.assertEqual(result["multiplier"], 3.0)

    def test_adjust_8h(self):
        result = adjust_estimate(480)
        self.assertEqual(result["adjusted_minutes"], 960)  # 8h × 2 = 16h

    def test_parse_estimate_minutes(self):
        self.assertEqual(parse_estimate("30 min"), 30.0)
        self.assertEqual(parse_estimate("90"), 90.0)  # default to min

    def test_parse_estimate_hours(self):
        self.assertEqual(parse_estimate("2.5 h"), 150.0)
        self.assertEqual(parse_estimate("1 hour"), 60.0)


class TestChunkHelper(unittest.TestCase):

    def test_chunk_8h(self):
        result = chunk_task(480)
        self.assertEqual(result["total_minutes"], 480)
        # Should be 5 phases
        self.assertEqual(len(result["phases"]), 5)
        # All chunks should be ≤50 min
        for ph in result["phases"]:
            for ch in ph["chunks"]:
                self.assertLessEqual(ch["minutes"], 50)
        # Sessions should be ≤180 min
        for sess in result["sessions"]:
            self.assertLessEqual(sess["total_minutes"], 180)

    def test_chunk_short(self):
        result = chunk_task(60)
        # Very small tasks still produce all phases (just very small chunks)
        self.assertEqual(result["total_minutes"], 60)


class TestSwitchTracker(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.vault = Path(self.tmpdir)

    def test_record_and_status(self):
        record_switch(self.vault, to_context="PROJECT-A", reason="session-start")
        record_switch(self.vault, from_context="PROJECT-A", to_context="PROJECT-B", reason="voluntary")
        status = get_status(self.vault)
        # 1 voluntary switch
        self.assertEqual(status["today"]["voluntary_switches"], 1)
        # focus_score = 100 - 20 = 80
        self.assertEqual(status["today"]["focus_score"], 80)
        self.assertFalse(status["today"]["over_budget"])

    def test_over_budget(self):
        for i in range(5):
            record_switch(self.vault, to_context=f"PROJECT-{i}", reason="voluntary")
        status = get_status(self.vault)
        self.assertEqual(status["today"]["voluntary_switches"], 5)
        self.assertTrue(status["today"]["over_budget"])
        # focus_score floors at 0
        self.assertEqual(status["today"]["focus_score"], 0)

    def test_compute_focus_score(self):
        # No switches = 100
        self.assertEqual(compute_focus_score([]), 100)
        # 1 voluntary = 80
        self.assertEqual(compute_focus_score([{"reason": "voluntary"}]), 80)
        # 2 voluntary = 60
        self.assertEqual(compute_focus_score([{"reason": "voluntary"}] * 2), 60)

    # ATTN-002: required JSON fields and append-only ledger

    # @spec ATTN-002
    def test_attn002_required_fields(self):
        """ATTN-002: each appended entry must contain from, to, timestamp, reason."""
        entry = record_switch(
            self.vault,
            from_context="PROJECT-A",
            to_context="PROJECT-B",
            reason="voluntary",
        )
        self.assertIn("from", entry)
        self.assertIn("to", entry)
        self.assertIn("timestamp", entry)
        self.assertIn("reason", entry)
        self.assertEqual(entry["from"], "PROJECT-A")
        self.assertEqual(entry["to"], "PROJECT-B")

    # @spec ATTN-002
    def test_attn002_from_is_optional(self):
        """ATTN-002: from is optional (first session has no previous project)."""
        entry = record_switch(self.vault, to_context="PROJECT-A", reason="session-start")
        self.assertIsNone(entry["from"])
        self.assertEqual(entry["to"], "PROJECT-A")

    # @spec ATTN-002, ATTN-008
    def test_attn002_append_only(self):
        """ATTN-002 + ATTN-008: each switch adds exactly one line; prior lines unchanged."""
        record_switch(self.vault, to_context="PROJECT-A", reason="session-start")
        record_switch(self.vault, from_context="PROJECT-A", to_context="PROJECT-B", reason="voluntary")
        record_switch(self.vault, from_context="PROJECT-B", to_context="PROJECT-C", reason="voluntary")

        log_path = self.vault / ".squirrel" / "switches.jsonl"
        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        self.assertEqual(len(lines), 3)

        parsed = [json.loads(l) for l in lines]
        self.assertEqual(parsed[0]["to"], "PROJECT-A")
        self.assertEqual(parsed[1]["from"], "PROJECT-A")
        self.assertEqual(parsed[1]["to"], "PROJECT-B")
        self.assertEqual(parsed[2]["from"], "PROJECT-B")
        self.assertEqual(parsed[2]["to"], "PROJECT-C")

    # @spec ATTN-002
    def test_attn002_jsonl_is_valid_json_per_line(self):
        """ATTN-002: every line in switches.jsonl must be valid JSON."""
        for i in range(3):
            record_switch(self.vault, to_context=f"P-{i}", reason="voluntary")

        log_path = self.vault / ".squirrel" / "switches.jsonl"
        for line in log_path.read_text().splitlines():
            if line.strip():
                json.loads(line)  # must not raise


class TestDeadlineClassification(unittest.TestCase):
    """ATTN-001: classify_urgency must return exactly one of the 6 canonical levels."""

    CANONICAL_LEVELS = {"critical", "urgent", "soon", "upcoming", "eventual", "distant"}

    def _now(self, **kwargs) -> "datetime.datetime":
        import datetime
        return datetime.datetime(2026, 6, 1, 10, 0, 0)  # fixed reference: 2026-06-01 10:00

    def _date(self, days_offset: int) -> "datetime.date":
        import datetime
        return (datetime.date(2026, 6, 1) + datetime.timedelta(days=days_offset))

    # @spec ATTN-001
    def test_urgency_levels_constant_matches_spec(self):
        """ATTN-001: URGENCY_LEVELS must be exactly the 6 canonical names."""
        self.assertEqual(set(URGENCY_LEVELS), self.CANONICAL_LEVELS)
        self.assertEqual(len(URGENCY_LEVELS), 6)

    # @spec ATTN-001
    def test_overdue_classified_as_critical(self):
        """ATTN-001: items past their deadline must land in 'critical' with is_overdue=True."""
        level, info = classify_urgency(self._date(-3), self._now())
        self.assertEqual(level, "critical")
        self.assertTrue(info.get("is_overdue"))
        self.assertEqual(info["days_overdue"], 3)

    # @spec ATTN-001
    def test_critical_imminent(self):
        """ATTN-001: deadline today with <4 h left → critical (no is_overdue)."""
        import datetime
        # 10:00 now, deadline today at 23:59 → ~13.9 h left → NOT critical by hours
        # Force near-expiry: set now to 22:00
        now = datetime.datetime(2026, 6, 1, 22, 0, 0)
        level, info = classify_urgency(self._date(0), now)
        self.assertEqual(level, "critical")
        self.assertFalse(info.get("is_overdue", False))

    # @spec ATTN-001
    def test_urgent_today_many_hours(self):
        """ATTN-001: deadline today with ≥4 h remaining → urgent."""
        level, info = classify_urgency(self._date(0), self._now())
        self.assertEqual(level, "urgent")

    # @spec ATTN-001
    def test_urgent_tomorrow(self):
        """ATTN-001: deadline tomorrow → urgent."""
        level, info = classify_urgency(self._date(1), self._now())
        self.assertEqual(level, "urgent")

    # @spec ATTN-001
    def test_soon(self):
        """ATTN-001: 2–3 days → soon."""
        for d in (2, 3):
            with self.subTest(days=d):
                level, _ = classify_urgency(self._date(d), self._now())
                self.assertEqual(level, "soon")

    # @spec ATTN-001
    def test_upcoming(self):
        """ATTN-001: 4–7 days → upcoming."""
        for d in (4, 7):
            with self.subTest(days=d):
                level, _ = classify_urgency(self._date(d), self._now())
                self.assertEqual(level, "upcoming")

    # @spec ATTN-001
    def test_eventual(self):
        """ATTN-001: 8–30 days → eventual."""
        for d in (8, 15, 30):
            with self.subTest(days=d):
                level, _ = classify_urgency(self._date(d), self._now())
                self.assertEqual(level, "eventual")

    # @spec ATTN-001
    def test_distant(self):
        """ATTN-001: >30 days → distant."""
        for d in (31, 60, 365):
            with self.subTest(days=d):
                level, _ = classify_urgency(self._date(d), self._now())
                self.assertEqual(level, "distant")

    # @spec ATTN-001
    def test_deterministic(self):
        """ATTN-001: same deadline + same now must always produce same level."""
        import datetime
        now = datetime.datetime(2026, 6, 1, 10, 0, 0)
        deadline = datetime.date(2026, 6, 10)
        results = {classify_urgency(deadline, now)[0] for _ in range(5)}
        self.assertEqual(len(results), 1)

    # @spec ATTN-001
    def test_each_result_is_canonical(self):
        """ATTN-001: every call must return a level from the canonical set."""
        import datetime
        now = datetime.datetime(2026, 6, 1, 10, 0, 0)
        for offset in (-5, -1, 0, 1, 2, 5, 10, 45):
            deadline = datetime.date(2026, 6, 1) + datetime.timedelta(days=offset)
            level, _ = classify_urgency(deadline, now)
            self.assertIn(level, self.CANONICAL_LEVELS, f"days_offset={offset} gave invalid level {level!r}")


class TestEndToEnd(unittest.TestCase):
    """Test that the CLI tools work end-to-end."""

    def test_intent_parser_cli(self):
        path = FIXTURES / "01-Active-Projects" / "TEST-PROJECT" / "TEST-PROJECT-AUTH-002.md"
        script = Path(__file__).parent.parent / "lib" / "intent_parser.py"
        result = subprocess.run(
            ["python3", str(script), str(path), "--field", "stats"],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        self.assertEqual(data["definition_of_done"]["percent_done"], 33)

    def test_status_aggregator_cli(self):
        script = Path(__file__).parent.parent / "lib" / "status_aggregator.py"
        result = subprocess.run(
            ["python3", str(script), "--vault", str(FIXTURES)],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        wip = data["wip"]

        # Drift-proof oracle: every folder under 01-Active-Projects counts
        # toward WIP (the WIP-cap contract — see
        # docs/lld/future-reminders-and-scratch-pad.md). Deriving the expected
        # count from the filesystem stops this smoke test from re-acquiring a
        # stale magic number whenever the fixture gains a project. The
        # load-bearing checks are the contract invariants below, not the raw
        # count. (Exact intended inventory lives in TestWipCount.)
        active_dir = FIXTURES / "01-Active-Projects"
        expected_wip = sum(1 for d in active_dir.iterdir() if d.is_dir())
        self.assertEqual(wip["count"], expected_wip)

        # Contract invariants — true regardless of how many fixtures exist:
        self.assertEqual(wip["count"], len(wip["projects"]))   # count matches payload
        self.assertEqual(wip["max"], 3)                        # cap constant
        self.assertEqual(wip["at_capacity"], wip["count"] >= wip["max"])
        over_cap = any(
            a["level"] == "warning" and "WIP excede" in a["message"]
            for a in data["alerts"]
        )
        self.assertEqual(over_cap, wip["count"] > wip["max"])  # warning iff over cap
        self.assertIsNotNone(data["recommended_focus"])

    def test_deadline_scanner_cli(self):
        script = Path(__file__).parent.parent / "lib" / "deadline_scanner.py"
        result = subprocess.run(
            ["python3", str(script), "--vault", str(FIXTURES)],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        self.assertGreater(data["total_intents_with_deadline"], 0)

    def test_deadline_scanner_level_filter(self):
        """R-1.2 — --level flag passes through and filters by_urgency keys."""
        script = Path(__file__).parent.parent / "lib" / "deadline_scanner.py"
        result = subprocess.run(
            ["python3", str(script), "--vault", str(FIXTURES), "--level", "critical,urgent"],
            capture_output=True, text=True, check=True,
        )
        data = json.loads(result.stdout)
        # Only requested levels present in by_urgency
        self.assertSetEqual(set(data["by_urgency"].keys()), {"critical", "urgent"})

    def test_deadline_scanner_missing_vault(self):
        """R-1.4 — non-zero exit when vault is missing."""
        script = Path(__file__).parent.parent / "lib" / "deadline_scanner.py"
        result = subprocess.run(
            ["python3", str(script), "--vault", "/nonexistent/vault"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)


class TestGpgHelpers(unittest.TestCase):
    """GPG helpers in package_protocol — unit tests that don't need gpg installed."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

    def test_gpg_available_returns_bool(self):
        from package_protocol import _gpg_available
        result = _gpg_available()
        self.assertIsInstance(result, bool)

    def test_read_gpg_recipient_missing_config(self):
        from package_protocol import _read_gpg_recipient
        # config may or may not exist; function must return str either way
        result = _read_gpg_recipient()
        self.assertIsInstance(result, str)

    def test_gpg_encrypt_no_gpg_raises(self):
        """gpg_encrypt raises RuntimeError when gpg is not available or key missing."""
        import shutil
        from package_protocol import gpg_encrypt
        if not shutil.which("gpg"):
            with self.assertRaises(RuntimeError):
                gpg_encrypt("hello", "nonexistent@example.com")
        else:
            # gpg is present but key doesn't exist — should also raise
            with self.assertRaises(RuntimeError):
                gpg_encrypt("hello", "no-such-key-abc123@example.com")

    def test_gpg_decrypt_invalid_raises(self):
        """gpg_decrypt raises RuntimeError on non-GPG input."""
        import shutil
        from package_protocol import gpg_decrypt
        if not shutil.which("gpg"):
            self.skipTest("gpg not installed")
        with self.assertRaises(RuntimeError):
            gpg_decrypt(b"this is not a gpg blob")

    def test_generate_cli_has_encrypt_flag(self):
        script = Path(__file__).parent.parent / "lib" / "package_protocol.py"
        result = subprocess.run(
            ["python3", str(script), "generate", "--help"],
            capture_output=True, text=True,
        )
        self.assertIn("--encrypt", result.stdout)
        self.assertIn("--gpg-recipient", result.stdout)

    def test_apply_cli_has_decrypt_flag(self):
        script = Path(__file__).parent.parent / "lib" / "package_protocol.py"
        result = subprocess.run(
            ["python3", str(script), "apply", "--help"],
            capture_output=True, text=True,
        )
        self.assertIn("--decrypt", result.stdout)


class TestTagParser(unittest.TestCase):
    """VAULT-003 — tag_parser.py (R-1.1 through R-1.9)."""

    def setUp(self):
        from tag_parser import validate, normalize, parse
        self.validate = validate
        self.normalize = normalize
        self.parse = parse

    # R-1.1 — valid tag
    def test_valid_tag_returns_true_none(self):
        ok, suggestion = self.validate("VISA-FAMILIA-TRAMITE-001")
        self.assertTrue(ok)
        self.assertIsNone(suggestion)

    # R-1.4 — un-padded suffix
    def test_unpadded_suffix_suggests_zero_padded(self):
        ok, suggestion = self.validate("VISA-FAMILIA-TRAMITE-1")
        self.assertFalse(ok)
        self.assertEqual(suggestion, "VISA-FAMILIA-TRAMITE-001")

    # R-1.5 — lowercase → uppercase suggestion
    def test_lowercase_suggests_uppercase(self):
        ok, suggestion = self.validate("visa-familia-tramite-001")
        self.assertFalse(ok)
        self.assertEqual(suggestion, "VISA-FAMILIA-TRAMITE-001")

    # R-1.5 + R-1.4 combined
    def test_lowercase_and_unpadded_suggests_corrected(self):
        ok, suggestion = self.validate("visa-familia-tramite-1")
        self.assertFalse(ok)
        self.assertEqual(suggestion, "VISA-FAMILIA-TRAMITE-001")

    # R-1.6 — too few named segments
    def test_two_segment_tag_is_structurally_invalid(self):
        ok, suggestion = self.validate("VISA-001")
        self.assertFalse(ok)
        self.assertIsNone(suggestion)

    # R-1.6 — three segments still invalid (needs 3 named + numeric)
    def test_three_segment_tag_is_structurally_invalid(self):
        ok, suggestion = self.validate("VISA-FAMILIA-001")
        self.assertFalse(ok)
        self.assertIsNone(suggestion)

    # R-1.7 — None input
    def test_none_returns_false_none(self):
        ok, suggestion = self.validate(None)
        self.assertFalse(ok)
        self.assertIsNone(suggestion)

    # R-1.7 — empty string
    def test_empty_string_returns_false_none(self):
        ok, suggestion = self.validate("")
        self.assertFalse(ok)
        self.assertIsNone(suggestion)

    # R-1.8 — CLI exits 0 for valid tag
    def test_cli_exits_0_for_valid_tag(self):
        script = Path(__file__).parent.parent / "lib" / "tag_parser.py"
        result = subprocess.run(
            ["python3", str(script), "VISA-FAMILIA-TRAMITE-001"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Valid", result.stdout)

    # R-1.8 — CLI exits 1 for invalid tag
    def test_cli_exits_1_for_invalid_tag(self):
        script = Path(__file__).parent.parent / "lib" / "tag_parser.py"
        result = subprocess.run(
            ["python3", str(script), "VISA-001"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid", result.stdout)


class TestSchemaVersion(unittest.TestCase):
    """VAULT-005 — schema_version in status_aggregator (R-2.1 through R-2.3)."""

    def setUp(self):
        from status_aggregator import aggregate_status
        self._vault = Path(__file__).parent / "fixtures" / "vault-minimal"
        self._output = aggregate_status(self._vault)

    # R-2.1 — field present
    def test_schema_version_key_present(self):
        self.assertIn("schema_version", self._output)

    # R-2.2 — value is string "001"
    def test_schema_version_value_is_string_001(self):
        self.assertEqual(self._output["schema_version"], "001")

    # R-2.3 — first key
    def test_schema_version_is_first_key(self):
        self.assertEqual(list(self._output.keys())[0], "schema_version")


class TestWipCount(unittest.TestCase):
    """Canonical WIP inventory for the minimal fixture.

    Every folder under 01-Active-Projects occupies a WIP slot — including the
    Scratch Pad and a deliberately stale project. Per
    docs/lld/future-reminders-and-scratch-pad.md: "The Scratch Pad counts toward
    the WIP cap like any other project." The cap is a load signal ("how many
    things are open"), not a progress signal; staleness is handled in
    recommended_focus, not by excluding the project from the count.

    This is the one place that pins the EXACT expected set. If you change the
    fixture, update this set intentionally — do not bump a number to make red
    go green. (The end-to-end smoke test stays drift-proof on purpose.)
    """

    EXPECTED_WIP = {"TEST-PROJECT", "SIDEPROJECT-STALE", "SCRATCH-PAD"}

    def setUp(self):
        from status_aggregator import aggregate_status
        self._output = aggregate_status(FIXTURES)

    def test_wip_set_is_the_known_fixture_projects(self):
        wip_slugs = {p["id"] for p in self._output["wip"]["projects"]}
        self.assertEqual(wip_slugs, self.EXPECTED_WIP)

    def test_wip_count_matches_the_set(self):
        self.assertEqual(
            self._output["wip"]["count"], len(self._output["wip"]["projects"])
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
