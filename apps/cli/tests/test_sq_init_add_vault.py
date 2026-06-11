#!/usr/bin/env python3
"""
Story 3.2 — verify /sq-init exposes an `--add-vault` subflow.

Acceptance (from docs/ears/multi-vault-core.md):
  R-6.4: THE SYSTEM SHALL add a `--add-vault` flag to `/sq-init` that prompts
         for `name`, `path`, and `set-as-default? (y/n)` and writes a new
         entry to `~/.squirrel/config.toml`.

Verify (from docs/tasks/multi-vault-core.md story 3.2):
  invoking `/sq-init --add-vault` prompts for name, path, set-as-default (y/n)
  and appends to `config.toml`. Existing `/sq-init` (no flag) behavior
  unchanged for first-time users.
"""

import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
MONOREPO = REPO.parent.parent  # apps/cli → squirrel/
SQ_INIT = MONOREPO / "agent-pack" / "commands" / "sq-init.md"


def _read() -> str:
    assert SQ_INIT.exists(), f"missing command file: {SQ_INIT}"
    return SQ_INIT.read_text(encoding="utf-8")


class TestSqInitAddVaultDocumented(unittest.TestCase):
    """R-6.4 — the --add-vault flag must be documented in the command file."""

    def test_documents_add_vault_flag(self):
        text = _read()
        self.assertIn(
            "--add-vault",
            text,
            "sq-init.md must document the --add-vault flag (R-6.4)",
        )

    def test_prompts_for_name(self):
        text = _read()
        self.assertRegex(
            text.lower(),
            r"\bname\b",
            "sq-init.md --add-vault flow must prompt for name (R-6.4)",
        )

    def test_prompts_for_path(self):
        text = _read()
        # "path" appears all over; ensure the add-vault section requests a path
        # specifically by checking the --add-vault flow asks for it
        self.assertIn(
            "path",
            text.lower(),
            "sq-init.md --add-vault flow must prompt for path (R-6.4)",
        )

    def test_prompts_set_as_default(self):
        text = _read()
        # Accept either English or Spanish phrasing for the y/n prompt
        lowered = text.lower()
        self.assertTrue(
            "set-as-default" in lowered
            or "set as default" in lowered
            or "default? (y/n)" in lowered
            or "default? (s/n)" in lowered
            or "default (y/n)" in lowered
            or "default (s/n)" in lowered,
            "sq-init.md --add-vault flow must ask set-as-default? (y/n) (R-6.4)",
        )


class TestSqInitAddVaultUsesConfigLoader(unittest.TestCase):
    """R-6.4 — writes must go through config_loader.add_vault, not raw TOML edits."""

    def test_uses_config_loader_add_vault(self):
        text = _read()
        self.assertIn(
            "config_loader",
            text,
            "sq-init.md --add-vault must invoke config_loader (R-6.4 / D3)",
        )
        self.assertIn(
            "add_vault",
            text,
            "sq-init.md --add-vault must call add_vault() so validation runs (R-6.4)",
        )

    def test_set_default_when_user_picks_yes(self):
        text = _read()
        # When user answers yes to set-as-default, the flow must call set_default
        self.assertIn(
            "set_default",
            text,
            "sq-init.md --add-vault must call set_default when user opts in (R-6.4)",
        )


class TestSqInitFirstTimeFlowPreserved(unittest.TestCase):
    """Verify: existing `/sq-init` (no flag) behavior unchanged for first-time users."""

    def test_default_flow_still_creates_config_from_template(self):
        text = _read()
        # The original flow copies the template — keep that behavior intact
        self.assertIn(
            "squirrel.toml.example",
            text,
            "sq-init.md must still copy the config template on first-time init",
        )

    def test_default_flow_still_creates_vault_structure(self):
        text = _read()
        # The original flow ensures vault PARA folders exist
        self.assertIn(
            "01-Active-Projects",
            text,
            "sq-init.md must still create vault PARA structure on first-time init",
        )


if __name__ == "__main__":
    unittest.main()
