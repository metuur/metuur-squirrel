#!/usr/bin/env python3
"""
Story 8.1 — verify lib/status_aggregator.active_intent_for.

Acceptance:
  - Returns the intent slug whose most recent shutdown note has the latest timestamp.
  - Returns None if no intent has any shutdown notes / activity.
  - Returns None if the project folder does not exist.
  - Mirrors the inlined logic at status_aggregator.py:163–181 without changing behaviour.
"""

import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from status_aggregator import active_intent_for  # noqa: E402


PROJECT_PAGE = """\
---
id: PROJECT-A
tipo: A
estado: in-progress
---
# PROJECT-A
"""

INTENT_TEMPLATE = """\
---
id: {intent_id}
estado: in-progress
---
# {intent_id} title

## Shutdown Notes

### {timestamp}
- **Estado**: in-progress
- **Next**: continue work
"""

INTENT_NO_NOTES = """\
---
id: {intent_id}
estado: pending
---
# {intent_id} title

## Shutdown Notes
"""


def _write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestActiveIntentFor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _project_dir(self, slug: str) -> pathlib.Path:
        return self.vault / "01-Proyectos-Activos" / slug

    def test_returns_more_recently_updated_intent(self):
        proj = self._project_dir("PROJECT-A")
        _write(proj / "PROJECT-A.md", PROJECT_PAGE)
        _write(
            proj / "PROJECT-A-i01.md",
            INTENT_TEMPLATE.format(intent_id="PROJECT-A-i01", timestamp="2026-05-20 09:00"),
        )
        _write(
            proj / "PROJECT-A-i02.md",
            INTENT_TEMPLATE.format(intent_id="PROJECT-A-i02", timestamp="2026-05-28 10:00"),
        )

        self.assertEqual(active_intent_for(self.vault, "PROJECT-A"), "PROJECT-A-i02")

    def test_returns_none_when_no_intent_has_activity(self):
        proj = self._project_dir("PROJECT-A")
        _write(proj / "PROJECT-A.md", PROJECT_PAGE)
        _write(
            proj / "PROJECT-A-i01.md",
            INTENT_NO_NOTES.format(intent_id="PROJECT-A-i01"),
        )
        _write(
            proj / "PROJECT-A-i02.md",
            INTENT_NO_NOTES.format(intent_id="PROJECT-A-i02"),
        )

        self.assertIsNone(active_intent_for(self.vault, "PROJECT-A"))

    def test_returns_none_when_project_folder_missing(self):
        (self.vault / "01-Proyectos-Activos").mkdir()
        # No PROJECT-A subfolder created.
        self.assertIsNone(active_intent_for(self.vault, "PROJECT-A"))

    def test_single_intent_with_activity_wins_over_intent_without(self):
        proj = self._project_dir("PROJECT-A")
        _write(proj / "PROJECT-A.md", PROJECT_PAGE)
        _write(
            proj / "PROJECT-A-i01.md",
            INTENT_TEMPLATE.format(intent_id="PROJECT-A-i01", timestamp="2026-05-15 08:00"),
        )
        _write(
            proj / "PROJECT-A-i02.md",
            INTENT_NO_NOTES.format(intent_id="PROJECT-A-i02"),
        )

        self.assertEqual(active_intent_for(self.vault, "PROJECT-A"), "PROJECT-A-i01")


if __name__ == "__main__":
    unittest.main()
