#!/usr/bin/env python3
"""
Story 1.1 — verify lib/intent_parser.write_frontmatter.

Acceptance (R-1.6, R-1.7):
  - read -> no-op write -> byte-identical file
  - mutations[k] == _DELETE removes the key entirely (no `k: null`, no `k: ""`)
  - upsert appends new keys at the end of the frontmatter block
  - update preserves the original position of the key
  - body is byte-identical
"""

import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from intent_parser import write_frontmatter, _DELETE  # noqa: E402


FIXTURE_WITH_FOCUS_TODAY = """---
id: TAG-001
# tracked by spec R-1.6
status: active
deadline: 2026-06-01
focus_today: 2026-05-01
tags: [intent, project/X]
---
# Title

## Objetivo

Some body content.

## Tareas

- [ ] task 1
- [x] task 2
"""

FIXTURE_WITHOUT_FOCUS_TODAY = """---
id: TAG-002
# tracked by spec R-1.6
status: active
deadline: 2026-06-01
tags: [intent, project/Y]
---
# Title

## Objetivo

Body content here.

## Notas

Some notes.
"""


class TestWriteFrontmatter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_fixture(self, name: str, content: str) -> pathlib.Path:
        p = self.dir / name
        p.write_text(content, encoding="utf-8")
        return p

    def test_roundtrip_noop_byte_identical(self):
        """R-1.6 — read -> no-op write -> byte-identical file."""
        p = self._write_fixture("intent.md", FIXTURE_WITH_FOCUS_TODAY)
        original = p.read_bytes()

        write_frontmatter(p, {})

        self.assertEqual(p.read_bytes(), original)

    def test_upsert_new_key_appended(self):
        """New key inserted at end of FM block; body unchanged."""
        p = self._write_fixture("intent.md", FIXTURE_WITHOUT_FOCUS_TODAY)
        original_lines = FIXTURE_WITHOUT_FOCUS_TODAY.splitlines()

        write_frontmatter(p, {"focus_today": "2026-05-28"})

        new_content = p.read_text(encoding="utf-8")
        new_lines = new_content.splitlines()

        # Body unchanged
        body_start_orig = original_lines.index("---", 1) + 1
        body_start_new = new_lines.index("---", 1) + 1
        self.assertEqual(original_lines[body_start_orig:], new_lines[body_start_new:])

        # focus_today appears in FM
        fm_section = new_lines[1:body_start_new - 1]
        focus_lines = [ln for ln in fm_section if ln.startswith("focus_today:")]
        self.assertEqual(len(focus_lines), 1)
        self.assertEqual(focus_lines[0].strip(), "focus_today: 2026-05-28")

        # New key was appended at end of FM (last non-empty line)
        non_empty = [ln for ln in fm_section if ln.strip()]
        self.assertEqual(non_empty[-1].strip(), "focus_today: 2026-05-28")

        # Other FM keys preserved in same order with same values
        orig_fm = original_lines[1:original_lines.index("---", 1)]
        orig_keys_lines = [ln for ln in orig_fm if ":" in ln and not ln.startswith(" ") and not ln.lstrip().startswith("#")]
        for ln in orig_keys_lines:
            self.assertIn(ln, fm_section)

    def test_delete_existing_key_removes_line(self):
        """R-1.7 — _DELETE drops the line; no `null` or `""` written."""
        p = self._write_fixture("intent.md", FIXTURE_WITH_FOCUS_TODAY)

        write_frontmatter(p, {"focus_today": _DELETE})

        new_content = p.read_text(encoding="utf-8")
        self.assertNotIn("focus_today:", new_content)
        self.assertNotIn("focus_today: null", new_content)
        self.assertNotIn('focus_today: ""', new_content)

        # Other keys preserved
        self.assertIn("id: TAG-001", new_content)
        self.assertIn("status: active", new_content)
        self.assertIn("deadline: 2026-06-01", new_content)
        self.assertIn("tags: [intent, project/X]", new_content)

        # Body preserved
        self.assertIn("# Title", new_content)
        self.assertIn("- [ ] task 1", new_content)
        self.assertIn("- [x] task 2", new_content)

    def test_update_existing_key_preserves_position(self):
        """Updating an existing key keeps it in its original FM position."""
        p = self._write_fixture("intent.md", FIXTURE_WITH_FOCUS_TODAY)

        write_frontmatter(p, {"focus_today": "2026-05-28"})

        new_content = p.read_text(encoding="utf-8")
        new_lines = new_content.splitlines()

        # Find positions of FM keys in original and new
        orig_lines = FIXTURE_WITH_FOCUS_TODAY.splitlines()
        orig_fm = orig_lines[1:orig_lines.index("---", 1)]
        new_fm = new_lines[1:new_lines.index("---", 1)]

        # focus_today should be at the same index as before
        orig_focus_idx = next(i for i, ln in enumerate(orig_fm) if ln.startswith("focus_today:"))
        new_focus_idx = next(i for i, ln in enumerate(new_fm) if ln.startswith("focus_today:"))
        self.assertEqual(orig_focus_idx, new_focus_idx)

        # New value applied
        self.assertEqual(new_fm[new_focus_idx].strip(), "focus_today: 2026-05-28")

        # Only that one line changed
        for i, (o, n) in enumerate(zip(orig_fm, new_fm)):
            if i == orig_focus_idx:
                continue
            self.assertEqual(o, n)


if __name__ == "__main__":
    unittest.main()
