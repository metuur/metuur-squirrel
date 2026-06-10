#!/usr/bin/env python3
"""Obsidian → squirrel-vault migration (docs/tasks/obsidian-vault-migration-skill.md, S1).

Acceptance:
  - plan maps: top-level folder → project (parking by default), folder-note →
    project page, other notes → intents, daily folder → 04-Daily, loose root
    notes → Inbox captures continuing UNFILED numbering, attachments copied
  - apply writes required frontmatter (id/project/status/created/tags),
    normalizes status values, preserves extra frontmatter keys and the body
  - apply never overwrites; re-apply is idempotent (all skipped)
  - the source vault is never modified
  - refuses a source that is already a squirrel vault
  - migrated projects are visible to aggregate_status() in the parking bucket
"""

import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from intent_parser import parse_frontmatter  # noqa: E402
from status_aggregator import aggregate_status  # noqa: E402
from vault_migrator import MigrationError, apply_plan, build_plan  # noqa: E402


def _snapshot(root: pathlib.Path) -> dict:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


class VaultMigratorTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self._tmp.name)
        self.source = tmp / "obsidian"
        self.vault = tmp / "squirrel-vault"
        self.vault.mkdir(parents=True)

        # Obsidian source: project folder with folder-note + plain note +
        # frontmatter note + nested note + attachment; daily folder; loose
        # root note; .obsidian to skip.
        proj = self.source / "My App"
        (proj / "nested").mkdir(parents=True)
        (proj / "My App.md").write_text("# My App\n\nThe folder note.\n", encoding="utf-8")
        (proj / "Auth ideas.md").write_text("Some auth thoughts, no frontmatter.\n", encoding="utf-8")
        (proj / "Login bug.md").write_text(
            "---\nstatus: Done\ncreated: 2025-03-04\npriority: high\ntags: [bug]\n---\n\n# Login bug\n\nFixed.\n",
            encoding="utf-8",
        )
        (proj / "nested" / "Deep note.md").write_text("Deep content.\n", encoding="utf-8")
        (proj / "diagram.png").write_bytes(b"\x89PNG fake")

        daily = self.source / "Daily Notes"
        daily.mkdir()
        (daily / "2025-01-01.md").write_text("New year note.\n", encoding="utf-8")

        (self.source / "Random thought.md").write_text("A loose root note.\n", encoding="utf-8")
        (self.source / ".obsidian").mkdir()
        (self.source / ".obsidian" / "app.json").write_text("{}", encoding="utf-8")

        # Pre-existing capture in the target Inbox: numbering must continue.
        inbox = self.vault / "99-Resources" / "Inbox"
        inbox.mkdir(parents=True)
        (inbox / "UNFILED-001.md").write_text("---\nid: UNFILED-001\n---\nexisting\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _plan(self, **kw):
        return build_plan(self.source, self.vault, **kw)

    # ── plan ────────────────────────────────────────────────────────────────

    def test_plan_maps_structure(self):
        plan = self._plan()
        self.assertEqual(len(plan["projects"]), 1)
        proj = plan["projects"][0]
        self.assertEqual(proj["tag"], "MY-APP")
        self.assertTrue(proj["page"]["from_note"].endswith("My App.md"))
        self.assertEqual(len(proj["intents"]), 3)  # folder-note excluded
        self.assertTrue(proj["page"]["target"].endswith("02-Parking-Lot/MY-APP/MY-APP.md"))
        self.assertEqual(len(plan["daily"]), 1)
        self.assertTrue(plan["daily"][0]["target"].endswith("04-Daily/2025-01-01.md"))
        self.assertEqual(len(plan["attachments"]), 1)
        self.assertIn("Obsidian-Attachments", plan["attachments"][0]["target"])
        # .obsidian content never appears anywhere in the plan
        for section in ("projects", "captures", "daily", "attachments"):
            self.assertNotIn(".obsidian", str(plan[section]))

    def test_plan_continues_unfiled_numbering(self):
        plan = self._plan()
        self.assertEqual(len(plan["captures"]), 1)
        self.assertTrue(plan["captures"][0]["target"].endswith("UNFILED-002.md"))

    def test_plan_dest_active(self):
        plan = self._plan(dest_bucket="01-Active-Projects")
        self.assertIn("01-Active-Projects/MY-APP", plan["projects"][0]["page"]["target"])

    def test_plan_refuses_squirrel_source(self):
        (self.source / "01-Active-Projects").mkdir()
        with self.assertRaises(MigrationError) as ctx:
            self._plan()
        self.assertEqual(ctx.exception.code, "SOURCE_INVALID")

    def test_plan_does_not_write_anything(self):
        before_src = _snapshot(self.source)
        before_vault = _snapshot(self.vault)
        self._plan()
        self.assertEqual(before_src, _snapshot(self.source))
        self.assertEqual(before_vault, _snapshot(self.vault))

    # ── apply ───────────────────────────────────────────────────────────────

    def test_apply_writes_project_page_and_intents(self):
        before_src = _snapshot(self.source)
        summary = apply_plan(self._plan())
        self.assertEqual(summary["skipped_count"], 0)

        page = self.vault / "02-Parking-Lot" / "MY-APP" / "MY-APP.md"
        fm, body = parse_frontmatter(page.read_text(encoding="utf-8"))
        self.assertEqual(fm["id"], "MY-APP")
        self.assertEqual(fm["type"], "C")
        self.assertIn("The folder note.", body)  # folder-note became the page

        intents = sorted((self.vault / "02-Parking-Lot" / "MY-APP").glob("MY-APP-NOTE-*.md"))
        self.assertEqual(len(intents), 3)
        by_origin = {}
        for p in intents:
            fm, body = parse_frontmatter(p.read_text(encoding="utf-8"))
            by_origin[fm["migrated_from"]] = (fm, body, p)
            self.assertEqual(fm["project"], "MY-APP")
            self.assertIn("intent", fm["tags"])
            self.assertIn("migrated/obsidian", fm["tags"])
            self.assertRegex(fm["created"], r"^\d{4}-\d{2}-\d{2}$")

        fm, body, _ = by_origin["My App/Login bug.md"]
        self.assertEqual(fm["status"], "done")          # "Done" normalized
        self.assertEqual(fm["created"], "2025-03-04")    # original date kept
        self.assertEqual(fm["priority"], "high")         # extra key preserved
        self.assertIn("bug", fm["tags"])                 # original tags merged
        self.assertIn("Fixed.", body)

        fm, body, _ = by_origin["My App/Auth ideas.md"]
        self.assertEqual(fm["status"], "pending")
        self.assertIn("# Auth ideas", body)              # H1 added when missing

        self.assertIn("My App/nested/Deep note.md", by_origin)

        # source untouched
        self.assertEqual(before_src, _snapshot(self.source))

    def test_apply_writes_capture_daily_attachment(self):
        apply_plan(self._plan())
        cap = self.vault / "99-Resources" / "Inbox" / "UNFILED-002.md"
        fm, body = parse_frontmatter(cap.read_text(encoding="utf-8"))
        self.assertEqual(fm["id"], "UNFILED-002")
        self.assertEqual(fm["type"], "capture")
        self.assertIn("A loose root note.", body)
        self.assertTrue((self.vault / "04-Daily" / "2025-01-01.md").is_file())
        att = self.vault / "99-Resources" / "Obsidian-Attachments" / "My App" / "diagram.png"
        self.assertEqual(att.read_bytes(), b"\x89PNG fake")

    def test_reapply_is_idempotent(self):
        plan = self._plan()
        first = apply_plan(plan)
        page = self.vault / "02-Parking-Lot" / "MY-APP" / "MY-APP.md"
        page.write_text(page.read_text(encoding="utf-8") + "\nuser edit\n", encoding="utf-8")
        second = apply_plan(plan)
        self.assertEqual(second["written_count"], 0)
        self.assertEqual(second["skipped_count"], first["written_count"])
        self.assertIn("user edit", page.read_text(encoding="utf-8"))  # not overwritten

    def test_migrated_project_visible_to_aggregator(self):
        apply_plan(self._plan())
        agg = aggregate_status(self.vault)
        parking_ids = [p["id"] for p in agg["parking_lot"]["items"]]
        self.assertIn("MY-APP", parking_ids)

    def test_apply_rejects_bad_plan(self):
        with self.assertRaises(MigrationError) as ctx:
            apply_plan({"schema": 99})
        self.assertEqual(ctx.exception.code, "PLAN_INVALID")

    def test_empty_source_raises(self):
        empty = pathlib.Path(self._tmp.name) / "empty"
        empty.mkdir()
        with self.assertRaises(MigrationError) as ctx:
            build_plan(empty, self.vault)
        self.assertEqual(ctx.exception.code, "NOTHING_TO_MIGRATE")


if __name__ == "__main__":
    unittest.main()
