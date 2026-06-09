#!/usr/bin/env python3
"""
Estimate↔Actual Reconciliation — engine + variance derivation.

Acceptance:
  R-1.1, R-1.6 — write 3 estimate keys atomically; leave time_invested_minutes + body untouched.
  R-1.3        — re-set overwrites.
  R-1.4, R-1.5 — resolution scoped to 01-Proyectos-Activos; out-of-scope / missing → error.
  R-1.7        — clear removes all 3 keys, keeps time_invested_minutes.
  R-2.7        — minutes bounds (0 / negative / >6000) rejected.
  R-3.1, R-3.3, R-3.6, R-5.2 — variance derivation w/ string coercion + graceful absence.
  R-5.3        — Quick Tasks are structurally unresolvable.
"""

import datetime
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

import estimate_buffer as eb  # noqa: E402
from focus_picker import get_manual_focus  # noqa: E402
from intent_parser import parse_intent  # noqa: E402


def _write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _intent(fm: dict, title: str = "An Intent") -> str:
    body = "\n".join(f"{k}: {v}" for k, v in fm.items())
    return f"---\n{body}\n---\n\n# {title}\n\nSome body text.\n"


class EstimateEngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = pathlib.Path(self.tmp.name)
        self.proj = self.vault / "01-Proyectos-Activos" / "PROJ"
        _write(self.proj / "PROJ.md", _intent({"id": "PROJ", "status": "wip"}, "Project"))
        _write(
            self.proj / "PROJ-001.md",
            _intent({"id": "PROJ-001", "status": "wip", "time_invested_minutes": 130}, "Task one"),
        )

    def tearDown(self):
        self.tmp.cleanup()

    # R-1.1 / R-1.6
    def test_apply_writes_three_keys_and_preserves_actual_and_body(self):
        stored = eb.apply_estimate_by_slugs(self.vault, "PROJ", "PROJ-001", 45)
        self.assertEqual(stored["estimate_user_minutes"], 45)
        self.assertEqual(stored["estimate_minutes"], int(45 * 2.5))  # 45 → 2.5x
        fm = parse_intent(self.proj / "PROJ-001.md")["frontmatter"]
        self.assertEqual(eb._coerce_num(fm.get("estimate_user_minutes")), 45)
        self.assertEqual(eb._coerce_num(fm.get("estimate_minutes")), int(45 * 2.5))
        self.assertEqual(eb._coerce_num(fm.get("time_invested_minutes")), 130)  # untouched
        self.assertIn("Some body text.", (self.proj / "PROJ-001.md").read_text())

    # R-1.3
    def test_re_set_overwrites(self):
        eb.apply_estimate_by_slugs(self.vault, "PROJ", "PROJ-001", 45)
        eb.apply_estimate_by_slugs(self.vault, "PROJ", "PROJ-001", 30)
        fm = parse_intent(self.proj / "PROJ-001.md")["frontmatter"]
        self.assertEqual(eb._coerce_num(fm.get("estimate_user_minutes")), 30)
        # exactly one occurrence of the key in the file
        self.assertEqual((self.proj / "PROJ-001.md").read_text().count("estimate_user_minutes:"), 1)

    # R-1.5 — missing intent
    def test_missing_intent_raises(self):
        with self.assertRaises(eb.EstimateError) as cm:
            eb.apply_estimate_by_slugs(self.vault, "PROJ", "NOPE", 45)
        self.assertEqual(cm.exception.code, "INTENT_NOT_FOUND")

    # R-1.4 / R-1.5 — out-of-scope (Areas) intent unresolvable by id
    def test_area_intent_out_of_scope(self):
        area = self.vault / "03-Areas"
        _write(area / "HEALTH.md", _intent({"id": "HEALTH", "status": "wip"}, "Health"))
        with self.assertRaises(eb.EstimateError):
            eb.resolve_wip_intent(self.vault, "HEALTH")

    # R-1.7 — clear
    def test_clear_removes_keys_keeps_actual(self):
        eb.apply_estimate_by_slugs(self.vault, "PROJ", "PROJ-001", 45)
        eb.clear_estimate_by_slugs(self.vault, "PROJ", "PROJ-001")
        text = (self.proj / "PROJ-001.md").read_text()
        self.assertNotIn("estimate_user_minutes", text)
        self.assertNotIn("estimate_minutes", text)
        self.assertNotIn("estimate_multiplier", text)
        self.assertIn("time_invested_minutes: 130", text)

    # R-2.7 — bounds
    def test_invalid_minutes_rejected(self):
        for bad in (0, -5, 99999):
            with self.assertRaises(eb.EstimateError):
                eb.apply_estimate_by_slugs(self.vault, "PROJ", "PROJ-001", bad)

    # R-5.3 — Quick Tasks structurally unresolvable
    def test_quick_task_not_resolvable(self):
        _write(
            self.proj / "QT-001.md",
            _intent({"id": "QT-001", "status": "open", "quick_task": "true", "type": "quick_task"}, "QT"),
        )
        with self.assertRaises(eb.EstimateError):
            eb.resolve_wip_intent(self.vault, "QT-001")

    # R-3.5 — variance flows into the manual-pick payload
    def test_variance_in_manual_pick(self):
        eb.apply_estimate_by_slugs(self.vault, "PROJ", "PROJ-001", 45)  # est 112, actual 130
        today = datetime.datetime(2026, 6, 6, 9, 0, 0)
        # tag the intent as today's focus so get_manual_focus surfaces it
        from intent_parser import write_frontmatter
        write_frontmatter(self.proj / "PROJ-001.md", {"focus_today": today.strftime("%Y-%m-%d")})
        pick = get_manual_focus(self.vault, now=today)["today"]
        self.assertIsNotNone(pick)
        self.assertTrue(pick["has_variance"])
        self.assertEqual(pick["estimate_user_minutes"], 45)
        self.assertEqual(pick["time_invested_minutes"], 130)
        self.assertAlmostEqual(pick["variance_ratio"], round(130 / int(45 * 2.5), 2))


class EstimateVarianceTest(unittest.TestCase):
    # R-3.1 / R-3.3 / R-3.6 — both sides as strings → numeric variance
    def test_both_present_strings(self):
        v = eb.estimate_variance({"estimate_minutes": "135", "estimate_user_minutes": "45",
                                  "time_invested_minutes": "130"})
        self.assertTrue(v["has_variance"])
        self.assertEqual(v["variance_minutes"], -5)
        self.assertAlmostEqual(v["variance_ratio"], round(130 / 135, 2))
        self.assertEqual(v["estimate_user_minutes"], 45)

    # R-4.5 — estimate only
    def test_estimate_only(self):
        v = eb.estimate_variance({"estimate_minutes": "135"})
        self.assertFalse(v["has_variance"])
        self.assertEqual(v["estimate_minutes"], 135)
        self.assertIsNone(v["time_invested_minutes"])

    # R-4.6 — actual only
    def test_actual_only(self):
        v = eb.estimate_variance({"time_invested_minutes": "130"})
        self.assertFalse(v["has_variance"])
        self.assertEqual(v["time_invested_minutes"], 130)
        self.assertIsNone(v["estimate_minutes"])

    # R-5.2 — malformed → absent, no raise
    def test_malformed_is_absent(self):
        v = eb.estimate_variance({"estimate_minutes": "abc", "time_invested_minutes": "130"})
        self.assertFalse(v["has_variance"])
        self.assertIsNone(v["estimate_minutes"])

    # R-5.1 — legacy (no keys) → safe empty
    def test_empty_frontmatter(self):
        v = eb.estimate_variance({})
        self.assertFalse(v["has_variance"])
        self.assertIsNone(v["estimate_minutes"])
        self.assertIsNone(v["time_invested_minutes"])


if __name__ == "__main__":
    unittest.main()
