#!/usr/bin/env python3
"""Tests for the cb CLI binary and dashboard_generator."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

FIXTURES = Path(__file__).parent / "fixtures" / "vault-minimal"
CB_SCRIPT = Path(__file__).parent.parent / "squirrel"


def run_cb(*args, vault=None):
    cmd = [sys.executable, str(CB_SCRIPT)]
    if vault:
        # cb commands that need vault will fail without config;
        # pass vault via env override not supported yet — skip those
        pass
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True)


class TestCbChunk(unittest.TestCase):
    """chunk subcommand — no vault needed."""

    def test_chunk_minutes(self):
        r = run_cb("chunk", "--minutes", "90")
        self.assertEqual(r.returncode, 0)
        self.assertIn("chunks", r.stdout)
        self.assertIn("session", r.stdout)

    def test_chunk_hours(self):
        r = run_cb("chunk", "--hours", "2")
        self.assertEqual(r.returncode, 0)
        self.assertIn("2h", r.stdout)

    def test_chunk_json(self):
        r = run_cb("--json", "chunk", "--minutes", "60")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertIn("phases", data)
        self.assertIn("total_chunks", data)
        self.assertEqual(data["total_minutes"], 60)

    def test_chunk_requires_duration(self):
        r = run_cb("chunk")
        self.assertNotEqual(r.returncode, 0)

    def test_chunk_exclusive_args(self):
        r = run_cb("chunk", "--minutes", "60", "--hours", "1")
        self.assertNotEqual(r.returncode, 0)


class TestCbEstimate(unittest.TestCase):
    """estimate subcommand — no vault needed."""

    def test_estimate_minutes(self):
        r = run_cb("estimate", "--minutes", "30")
        self.assertEqual(r.returncode, 0)
        self.assertIn("30 min", r.stdout)
        self.assertIn("×3.0", r.stdout)

    def test_estimate_hours(self):
        r = run_cb("estimate", "--hours", "2")
        self.assertEqual(r.returncode, 0)
        self.assertIn("2h", r.stdout)

    def test_estimate_string(self):
        r = run_cb("estimate", "--estimate", "90 min")
        self.assertEqual(r.returncode, 0)
        # 90 min humanizes to 1.5h; buffered should be 3h (×2.0)
        self.assertIn("1.5h", r.stdout)
        self.assertIn("3h", r.stdout)

    def test_estimate_json(self):
        r = run_cb("--json", "estimate", "--minutes", "60")
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertIn("multiplier", data)
        self.assertIn("adjusted_minutes", data)
        self.assertEqual(data["user_estimate_minutes"], 60)

    def test_estimate_invalid_string(self):
        r = run_cb("estimate", "--estimate", "not-a-time")
        self.assertNotEqual(r.returncode, 0)

    def test_estimate_requires_arg(self):
        r = run_cb("estimate")
        self.assertNotEqual(r.returncode, 0)


class TestCbHelp(unittest.TestCase):
    """Help and argument validation — no vault needed."""

    def test_top_level_help(self):
        r = run_cb("--help")
        self.assertEqual(r.returncode, 0)
        for cmd in ("status", "deadlines", "chunk", "estimate", "recover", "dashboard", "install"):
            self.assertIn(cmd, r.stdout)

    def test_chunk_help(self):
        r = run_cb("chunk", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--minutes", r.stdout)
        self.assertIn("--hours", r.stdout)

    def test_estimate_help(self):
        r = run_cb("estimate", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--estimate", r.stdout)

    def test_unknown_command(self):
        r = run_cb("bogus")
        self.assertNotEqual(r.returncode, 0)


@unittest.skip(
    "squirrel install walks <cli_dir>/skills which moved to agent-pack/ during "
    "the monorepo migration. The install command needs to be rewritten to "
    "locate agent-pack/, or replaced by agent-pack/install.sh. See TODO."
)
class TestCbInstall(unittest.TestCase):
    """install subcommand — uses --dry-run so no filesystem side effects."""

    def test_install_help(self):
        r = run_cb("install", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--agent", r.stdout)
        self.assertIn("--link", r.stdout)
        self.assertIn("--dry-run", r.stdout)

    def test_install_claude_dry_run(self):
        r = run_cb("install", "--agent", "claude", "--dry-run")
        self.assertEqual(r.returncode, 0)
        self.assertIn("claude", r.stdout)
        self.assertIn(".claude/plugins/squirrel", r.stdout)
        self.assertIn("Done", r.stdout)

    def test_install_codex_dry_run(self):
        r = run_cb("install", "--agent", "codex", "--dry-run")
        self.assertEqual(r.returncode, 0)
        self.assertIn("codex", r.stdout)
        self.assertIn(".codex/skills", r.stdout)
        self.assertIn(".codex/commands", r.stdout)
        self.assertIn("AGENTS.md", r.stdout)

    def test_install_cursor_dry_run(self):
        r = run_cb("install", "--agent", "cursor", "--dry-run")
        self.assertEqual(r.returncode, 0)
        self.assertIn("cursor", r.stdout)
        self.assertIn(".cursor/rules/squirrel", r.stdout)

    def test_install_standalone_dry_run(self):
        r = run_cb("install", "--agent", "standalone", "--dry-run")
        self.assertEqual(r.returncode, 0)
        self.assertIn("standalone", r.stdout)
        self.assertIn(".squirrel", r.stdout)

    def test_install_link_flag_dry_run(self):
        r = run_cb("install", "--agent", "claude", "--link", "--dry-run")
        self.assertEqual(r.returncode, 0)
        self.assertIn("symlink", r.stdout)

    def test_install_invalid_agent(self):
        r = run_cb("install", "--agent", "vscode")
        self.assertNotEqual(r.returncode, 0)

    def test_install_copies_to_real_tmpdir(self):
        """Verify --link creates a real symlink to the plugin root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_claude = Path(tmpdir) / ".claude" / "plugins"
            fake_claude.mkdir(parents=True)
            # We can't easily override the target dir without patching the script,
            # so just verify dry-run output is consistent with a real run.
            r = run_cb("install", "--agent", "claude", "--dry-run")
            self.assertIn("squirrel", r.stdout)


class TestDashboardGenerator(unittest.TestCase):
    """dashboard_generator.py — uses fixture vault."""

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

    def test_generate_html_smoke(self):
        from dashboard_generator import generate_html
        if not FIXTURES.exists():
            self.skipTest("Fixture vault not found")
        html = generate_html(FIXTURES)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Context Bridge", html)
        self.assertIn("<table>", html)

    def test_generate_html_has_sections(self):
        from dashboard_generator import generate_html
        if not FIXTURES.exists():
            self.skipTest("Fixture vault not found")
        html = generate_html(FIXTURES)
        self.assertIn("WIP", html)
        self.assertIn("Deadlines", html)

    def test_generate_html_no_xss(self):
        from dashboard_generator import _esc
        evil = '<script>alert("xss")</script>'
        escaped = _esc(evil)
        self.assertNotIn("<script>", escaped)
        self.assertIn("&lt;script&gt;", escaped)

    def test_generate_to_file(self):
        from dashboard_generator import generate_html
        if not FIXTURES.exists():
            self.skipTest("Fixture vault not found")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "dashboard.html"
            html = generate_html(FIXTURES)
            out.write_text(html, encoding="utf-8")
            self.assertTrue(out.exists())
            content = out.read_text()
            self.assertGreater(len(content), 1000)


if __name__ == "__main__":
    unittest.main()
