#!/usr/bin/env python3
"""
Story 1.2 + 2.1 + 2.2 — verify lib/focus_picker.

Acceptance:
  R-1.1, R-1.2 — Write focus_today: YYYY-MM-DD or focus_week: GGGG-Www.
  R-1.3        — Local timezone semantics for "now".
  R-1.4, R-1.5 — Stale values are ignored on read.
  R-1.8        — All I/O stays inside the vault.
  R-2.1–R-2.5  — Strip-before-write + don't cross-contaminate slots; leave stale alone.
  R-2.6        — On duplicates, most-recent mtime wins; no error.
  R-9.3, R-9.4 — No background process; expiry is read-time only.
"""

import datetime
import os
import pathlib
import sys
import tempfile
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from focus_picker import (  # noqa: E402
    IntentNotFound,
    _token_now,
    clear_manual_focus,
    get_manual_focus,
    set_manual_focus,
)


FROZEN_NOW = datetime.datetime(2026, 5, 28, 12, 0, 0)  # Thu, week W22
TODAY_TOKEN = "2026-05-28"
WEEK_TOKEN = "2026-W22"
STALE_DATE = "2026-05-27"


# ─────────────────────────────────────────────────────────────────────────────
# Fixture helpers
# ─────────────────────────────────────────────────────────────────────────────

def _format_fm(fm: dict) -> str:
    if not fm:
        return ""
    return "\n".join(f"{k}: {v}" for k, v in fm.items()) + "\n"


def _make_intent(
    folder: pathlib.Path,
    slug: str,
    frontmatter: dict,
    title: str = "An Intent",
) -> pathlib.Path:
    """Write a minimal valid intent .md and return its path."""
    folder.mkdir(parents=True, exist_ok=True)
    fm = {"id": slug, "status": "in-progress"}
    fm.update(frontmatter)
    content = (
        "---\n"
        + _format_fm(fm)
        + "---\n"
        + f"\n# {title}\n"
        + "\n## Shutdown Notes\n"
        + "\n### 2026-05-28 10:00\n"
        + "- **Estado**: in-progress\n"
        + "- **Next**: continue building\n"
    )
    p = folder / f"{slug}.md"
    p.write_text(content, encoding="utf-8")
    return p


def _make_project_page(folder: pathlib.Path, slug: str, title: str) -> pathlib.Path:
    folder.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        f"id: {slug}\n"
        "tipo: A\n"
        "estado: in-progress\n"
        "---\n"
        f"\n# {title}\n"
    )
    p = folder / f"{slug}.md"
    p.write_text(content, encoding="utf-8")
    return p


def _snapshot_vault(vault: pathlib.Path) -> dict:
    """Map of relative path -> raw bytes, for mutation comparisons."""
    snap = {}
    for f in vault.rglob("*.md"):
        snap[str(f.relative_to(vault))] = f.read_bytes()
    return snap


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTokenNow(unittest.TestCase):
    def test_today_token_format(self):
        self.assertEqual(_token_now("today", now=FROZEN_NOW), TODAY_TOKEN)

    def test_week_token_format(self):
        self.assertEqual(_token_now("week", now=FROZEN_NOW), WEEK_TOKEN)

    def test_iso_week_token_format(self):
        """R-1.2, R-1.3 — Monday and Sunday of the same ISO week produce the same token."""
        monday = datetime.datetime(2026, 5, 25, 8, 0, 0)
        sunday = datetime.datetime(2026, 5, 31, 23, 0, 0)
        self.assertEqual(_token_now("week", now=monday), _token_now("week", now=sunday))
        self.assertEqual(_token_now("week", now=monday), "2026-W22")

    def test_invalid_slot_raises(self):
        with self.assertRaises(ValueError):
            _token_now("month", now=FROZEN_NOW)

    def test_no_now_uses_wall_clock(self):
        # Should not raise and should return a string of the right shape.
        today = _token_now("today")
        week = _token_now("week")
        self.assertRegex(today, r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(week, r"^\d{4}-W\d{2}$")


class TestFocusPickerBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = pathlib.Path(self.tmp.name)
        self.wip = self.vault / "01-Active-Projects"
        self.wip.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _project(self, slug: str, title: str = None) -> pathlib.Path:
        folder = self.wip / slug
        _make_project_page(folder, slug, title or slug)
        return folder


class TestGetManualFocus(TestFocusPickerBase):
    def test_get_returns_today_intent_when_token_matches(self):
        proj = self._project("PROJECT-A", "Project A Title")
        _make_intent(proj, "PROJECT-A-i01", {"focus_today": TODAY_TOKEN}, title="Build the thing")
        _make_intent(proj, "PROJECT-A-i02", {"focus_today": STALE_DATE}, title="Stale one")
        _make_intent(proj, "PROJECT-A-i03", {}, title="No key")

        result = get_manual_focus(self.vault, now=FROZEN_NOW)
        self.assertIsNotNone(result["today"])
        self.assertEqual(result["today"]["intent_slug"], "PROJECT-A-i01")
        self.assertEqual(result["today"]["picked_on"], TODAY_TOKEN)
        self.assertEqual(result["today"]["project_slug"], "PROJECT-A")
        self.assertEqual(result["today"]["project_title"], "Project A Title")
        self.assertEqual(result["today"]["intent_title"], "Build the thing")
        self.assertEqual(result["today"]["next_action"], "continue building")
        self.assertIsNone(result["week"])

    def test_get_ignores_stale_today_token(self):
        proj = self._project("PROJECT-A")
        i_today = _make_intent(proj, "PROJECT-A-i01", {"focus_today": TODAY_TOKEN})
        i_stale = _make_intent(proj, "PROJECT-A-i02", {"focus_today": STALE_DATE})
        before = i_stale.read_bytes()

        result = get_manual_focus(self.vault, now=FROZEN_NOW)
        self.assertEqual(result["today"]["intent_slug"], "PROJECT-A-i01")
        # File for the stale intent is unchanged.
        self.assertEqual(i_stale.read_bytes(), before)
        # Also for the today one (read is non-mutating).
        self.assertIn(b"focus_today: 2026-05-28", i_today.read_bytes())

    def test_get_returns_none_for_unset_slot(self):
        proj = self._project("PROJECT-A")
        _make_intent(proj, "PROJECT-A-i01", {})
        result = get_manual_focus(self.vault, now=FROZEN_NOW)
        self.assertIsNone(result["today"])
        self.assertIsNone(result["week"])

    def test_get_picks_most_recent_mtime_on_duplicates(self):
        """R-2.6 — duplicates resolved by most recent mtime, no error."""
        proj_a = self._project("PROJECT-A")
        proj_b = self._project("PROJECT-B")
        older = _make_intent(proj_a, "PROJECT-A-i01", {"focus_today": TODAY_TOKEN})
        newer = _make_intent(proj_b, "PROJECT-B-i01", {"focus_today": TODAY_TOKEN})

        # Force older to be older, newer to be newer (with a healthy gap).
        old_t = time.time() - 1000
        new_t = time.time()
        os.utime(older, (old_t, old_t))
        os.utime(newer, (new_t, new_t))

        result = get_manual_focus(self.vault, now=FROZEN_NOW)
        self.assertEqual(result["today"]["intent_slug"], "PROJECT-B-i01")
        self.assertEqual(result["today"]["project_slug"], "PROJECT-B")


class TestSetManualFocus(TestFocusPickerBase):
    def test_set_strips_existing_token_and_writes_new(self):
        """R-2.1, R-2.4 — strip-before-write yields a single key on the new file."""
        proj_a = self._project("PROJECT-A")
        proj_b = self._project("PROJECT-B")
        dup1 = _make_intent(proj_a, "PROJECT-A-i01", {"focus_today": TODAY_TOKEN})
        dup2 = _make_intent(proj_a, "PROJECT-A-i02", {"focus_today": TODAY_TOKEN})
        target = _make_intent(proj_b, "PROJECT-B-i01", {})

        set_manual_focus(
            self.vault, "today", "PROJECT-B", "PROJECT-B-i01", now=FROZEN_NOW,
        )

        # Exactly one file has focus_today: TODAY_TOKEN, and it's the new target.
        carrying = []
        for f in self.vault.rglob("*.md"):
            if f"focus_today: {TODAY_TOKEN}" in f.read_text(encoding="utf-8"):
                carrying.append(f)
        self.assertEqual(len(carrying), 1)
        self.assertEqual(carrying[0], target)
        # Originals lose the key entirely.
        self.assertNotIn("focus_today", dup1.read_text(encoding="utf-8"))
        self.assertNotIn("focus_today", dup2.read_text(encoding="utf-8"))

    def test_set_today_does_not_touch_focus_week(self):
        """R-2.3 — setting today leaves focus_week alone."""
        proj_a = self._project("PROJECT-A")
        proj_b = self._project("PROJECT-B")
        original = _make_intent(
            proj_a, "PROJECT-A-i01",
            {"focus_today": TODAY_TOKEN, "focus_week": WEEK_TOKEN},
        )
        _make_intent(proj_b, "PROJECT-B-i01", {})

        set_manual_focus(
            self.vault, "today", "PROJECT-B", "PROJECT-B-i01", now=FROZEN_NOW,
        )

        content = original.read_text(encoding="utf-8")
        self.assertNotIn("focus_today", content)
        self.assertIn(f"focus_week: {WEEK_TOKEN}", content)

    def test_strip_leaves_stale_tokens_alone(self):
        """R-2.5 — strip is bounded to the current token; stale entries are left."""
        proj_a = self._project("PROJECT-A")
        proj_b = self._project("PROJECT-B")
        stale = _make_intent(proj_a, "PROJECT-A-i01", {"focus_today": STALE_DATE})
        _make_intent(proj_b, "PROJECT-B-i01", {})

        set_manual_focus(
            self.vault, "today", "PROJECT-B", "PROJECT-B-i01", now=FROZEN_NOW,
        )

        # Stale file still has its old token.
        self.assertIn(
            f"focus_today: {STALE_DATE}",
            stale.read_text(encoding="utf-8"),
        )

    def test_set_unknown_intent_raises(self):
        proj = self._project("PROJECT-A")
        _make_intent(proj, "PROJECT-A-i01", {})
        before = _snapshot_vault(self.vault)

        with self.assertRaises(IntentNotFound) as ctx:
            set_manual_focus(
                self.vault, "today", "NOPE", "NOPE", now=FROZEN_NOW,
            )
        self.assertEqual(ctx.exception.project_slug, "NOPE")
        self.assertEqual(ctx.exception.intent_slug, "NOPE")

        after = _snapshot_vault(self.vault)
        self.assertEqual(before, after)

    def test_idempotent_set(self):
        """R-2.4 — calling set twice with the same target yields a single key."""
        proj = self._project("PROJECT-A")
        target = _make_intent(proj, "PROJECT-A-i01", {})

        set_manual_focus(
            self.vault, "today", "PROJECT-A", "PROJECT-A-i01", now=FROZEN_NOW,
        )
        set_manual_focus(
            self.vault, "today", "PROJECT-A", "PROJECT-A-i01", now=FROZEN_NOW,
        )

        carrying = [
            f for f in self.vault.rglob("*.md")
            if f"focus_today: {TODAY_TOKEN}" in f.read_text(encoding="utf-8")
        ]
        self.assertEqual(len(carrying), 1)
        self.assertEqual(carrying[0], target)

    def test_set_week_slot_writes_iso_week_token(self):
        proj = self._project("PROJECT-A")
        target = _make_intent(proj, "PROJECT-A-i01", {})

        set_manual_focus(
            self.vault, "week", "PROJECT-A", "PROJECT-A-i01", now=FROZEN_NOW,
        )

        self.assertIn(
            f"focus_week: {WEEK_TOKEN}",
            target.read_text(encoding="utf-8"),
        )


class TestClearManualFocus(TestFocusPickerBase):
    def test_clear_removes_key_from_all_matching_intents(self):
        proj_a = self._project("PROJECT-A")
        proj_b = self._project("PROJECT-B")
        a = _make_intent(proj_a, "PROJECT-A-i01", {"focus_today": TODAY_TOKEN})
        b = _make_intent(proj_b, "PROJECT-B-i01", {"focus_today": TODAY_TOKEN})

        clear_manual_focus(self.vault, "today", now=FROZEN_NOW)

        for p in (a, b):
            content = p.read_text(encoding="utf-8")
            self.assertNotIn("focus_today", content)
            # Body still present.
            self.assertIn("# An Intent", content)

    def test_clear_leaves_stale_tokens_alone(self):
        proj = self._project("PROJECT-A")
        stale = _make_intent(proj, "PROJECT-A-i01", {"focus_today": STALE_DATE})
        before = stale.read_bytes()

        clear_manual_focus(self.vault, "today", now=FROZEN_NOW)
        self.assertEqual(stale.read_bytes(), before)


# ─────────────────────────────────────────────────────────────────────────────
# Story 2.1 — today_pm slot (R-1.1, R-1.2)
# ─────────────────────────────────────────────────────────────────────────────

from focus_picker import _slot_key  # noqa: E402  (already imported via focus_picker)


FROZEN_PM = datetime.datetime(2026, 5, 30, 14, 0, 0)


class TestTodayPmSlot(unittest.TestCase):
    def test_token_now_today_pm_format(self):
        """R-1.1 — today_pm token is YYYY-MM-DD-PM."""
        self.assertEqual(_token_now("today_pm", now=FROZEN_PM), "2026-05-30-PM")

    def test_slot_key_today_pm(self):
        """R-1.2 — slot key for today_pm is focus_today_pm."""
        self.assertEqual(_slot_key("today_pm"), "focus_today_pm")

    def test_invalid_slot_still_raises(self):
        """Invalid slot raises ValueError regardless of today_pm addition."""
        with self.assertRaises(ValueError):
            _token_now("invalid_slot", now=FROZEN_PM)

    def test_token_now_today_pm_uses_local_date(self):
        """Date portion of today_pm token matches local date of frozen clock."""
        token = _token_now("today_pm", now=FROZEN_PM)
        self.assertTrue(token.startswith("2026-05-30-"), token)
        self.assertTrue(token.endswith("-PM"), token)


if __name__ == "__main__":
    unittest.main()
