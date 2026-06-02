#!/usr/bin/env python3
"""
Story 2.1 — verify lib/vocabulary.py translations.

Acceptance (from docs/ears/web-ui-simple.md):
  R-4.1: lib/vocabulary.py exists and translates internal terms.
  R-4.5: project tag -> human title from project page; fallback to
         capitalized slug if no title.
  R-4.6: urgency -> friendly time mapping.
"""

import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from vocabulary import (  # noqa: E402
    FORBIDDEN_IN_USER_HTML,
    forbidden_terms,
    project_title,
    translate,
    urgency_label,
    workspace_word,
)


class TestPARAFolderTranslation(unittest.TestCase):
    def test_active_projects_maps_to_my_projects(self):
        self.assertEqual(translate("01-Proyectos-Activos"), "My projects")

    def test_parking_lot_maps_to_on_hold(self):
        self.assertEqual(translate("02-Parking-Lot"), "On hold")

    def test_areas_resources_archive_are_admin_only(self):
        self.assertEqual(translate("02-Areas"), "Areas")
        self.assertEqual(translate("03-Recursos"), "Reference")
        self.assertEqual(translate("04-Archivo"), "Archive")

    def test_resources_root_never_user_visible(self):
        self.assertIsNone(translate("99-Resources"))


class TestNoteTypeTranslation(unittest.TestCase):
    def test_intent_and_capture_collapse_to_note(self):
        self.assertEqual(translate("intent"), "note")
        self.assertEqual(translate("capture"), "note")

    def test_decision_visible_but_not_as_adr(self):
        self.assertEqual(translate("decision"), "important note")

    def test_shutdown_note_renamed_to_session_summary(self):
        self.assertEqual(translate("shutdown note"), "session summary")


class TestForbiddenTerms(unittest.TestCase):
    """R-4.2 / R-4.3 / R-4.4 — words that must never reach user HTML."""

    def test_frontmatter_concepts_never_user_visible(self):
        for term in ("frontmatter", "type", "status", "project", "wiki-link"):
            with self.subTest(term=term):
                self.assertIsNone(translate(term))

    def test_md_extension_never_user_visible(self):
        self.assertIsNone(translate(".md"))

    def test_parakeet_concept_never_user_visible(self):
        self.assertIsNone(translate("parakeet"))

    def test_vault_hidden_when_single_vault(self):
        # R-4.2 — single vault: the word is forbidden.
        self.assertIn("vault", forbidden_terms(multi_vault=False))
        self.assertIsNone(translate("vault", multi_vault=False))
        self.assertIsNone(workspace_word(multi_vault=False))

    def test_vault_becomes_workspace_when_multi_vault(self):
        # R-4.3 — multi-vault: render as "workspace", not "vault".
        self.assertNotIn("vault", forbidden_terms(multi_vault=True))
        self.assertEqual(translate("vault", multi_vault=True), "workspace")
        self.assertEqual(workspace_word(multi_vault=True), "workspace")

    def test_full_forbidden_set_matches_spec(self):
        # R-4.4 — these must always be forbidden in user-visible HTML.
        expected = {
            "frontmatter",
            "PARA",
            "intent",
            "wiki-link",
            ".md",
            "project",
            "type",
            "status",
            "01-Proyectos-Activos",
            "02-Areas",
            "03-Recursos",
            "04-Archivo",
            "02-Parking-Lot",
            "99-Resources",
            "shutdown note",
            "parakeet",
        }
        self.assertEqual(FORBIDDEN_IN_USER_HTML, frozenset(expected))


class TestUrgencyLabel(unittest.TestCase):
    """R-4.6 — urgency level to friendly time grouping."""

    def test_critical_and_urgent_map_to_today_tomorrow(self):
        self.assertEqual(urgency_label("critical"), "Today / Tomorrow")
        self.assertEqual(urgency_label("urgent"), "Today / Tomorrow")

    def test_soon_maps_to_this_week(self):
        self.assertEqual(urgency_label("soon"), "This week")

    def test_upcoming_eventual_distant_map_to_later(self):
        for lvl in ("upcoming", "eventual", "distant", "future_fyi"):
            with self.subTest(level=lvl):
                self.assertEqual(urgency_label(lvl), "Later")

    def test_unknown_level_falls_back_to_later(self):
        # Defensive: unknown levels never leak developer vocabulary.
        self.assertEqual(urgency_label("zzz"), "Later")

    def test_overdue_renders_as_today_overdue(self):
        self.assertEqual(urgency_label("overdue"), "Today / Overdue")


class TestProjectTitle(unittest.TestCase):
    """R-4.5 — slug to human title from project page."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = pathlib.Path(self.tmp.name)
        proj_dir = self.vault / "01-Proyectos-Activos" / "MY-BLOG"
        proj_dir.mkdir(parents=True)
        (proj_dir / "MY-BLOG.md").write_text(
            "---\n"
            "id: MY-BLOG\n"
            "tipo: B\n"
            "---\n\n"
            "# My Personal Blog\n\n"
            "Some body.\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_reads_first_heading_after_frontmatter(self):
        self.assertEqual(
            project_title("MY-BLOG", self.vault), "My Personal Blog"
        )

    def test_falls_back_to_capitalized_slug_when_no_project_page(self):
        self.assertEqual(
            project_title("UNKNOWN-PROJECT", self.vault),
            "Unknown Project",
        )

    def test_falls_back_when_vault_path_is_none(self):
        self.assertEqual(project_title("MY-BLOG"), "My Blog")


if __name__ == "__main__":
    unittest.main()
