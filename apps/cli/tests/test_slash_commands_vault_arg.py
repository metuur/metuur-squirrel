#!/usr/bin/env python3
"""
Story 3.1 — verify slash command `.md` files accept `--vault NAME`.

Acceptance (from docs/ears/multi-vault-core.md):
  R-6.1: vault-touching commands accept optional --vault NAME
  R-6.2: when --vault NAME is present, every `python3 lib/...` call in the
         bash block forwards --vault to the underlying script
  R-6.3: when --vault is absent, the flag is omitted so scripts use the default
  R-6.5: sq-chunk and sq-estimate are unchanged (vault-independent)
"""

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
MONOREPO = REPO.parent.parent  # apps/cli → squirrel/
COMMANDS_DIR = MONOREPO / "agent-pack" / "commands"

# R-6.1 — the 15 vault-touching slash commands
VAULT_TOUCHING_COMMANDS = [
    "sq-status",
    "sq-deadlines",
    "sq-where-am-i",
    "sq-start",
    "sq-end",
    "sq-capture",
    "sq-brief",
    "sq-decision",
    "sq-recover",
    "sq-chunk-intent",
    "sq-task-initiation",
    "sq-parakeet",
    "sq-dashboard",
    "sq-sync-out",
    "sq-sync-in",
]

# R-6.5 — vault-independent commands MUST NOT mention --vault
VAULT_INDEPENDENT_COMMANDS = ["sq-chunk", "sq-estimate"]


def _read(name: str) -> str:
    p = COMMANDS_DIR / f"{name}.md"
    assert p.exists(), f"missing command file: {p}"
    return p.read_text(encoding="utf-8")


class TestVaultArgInFrontmatter(unittest.TestCase):
    """R-6.1 — every vault-touching command documents --vault NAME."""

    def test_all_vault_touching_commands_mention_vault_arg(self):
        for name in VAULT_TOUCHING_COMMANDS:
            with self.subTest(command=name):
                text = _read(name)
                self.assertIn(
                    "--vault",
                    text,
                    msg=f"{name}.md must document --vault NAME (R-6.1)",
                )


class TestVaultArgForwardedInBashBlocks(unittest.TestCase):
    """R-6.2 / R-6.3 — commands with real bash blocks parse and forward --vault."""

    BASH_BLOCK_COMMANDS = ["sq-status", "sq-deadlines", "sq-parakeet", "sq-dashboard"]

    def test_bash_block_commands_parse_vault_from_arguments(self):
        # Each command with a python3-lib bash block must extract VAULT_NAME
        for name in self.BASH_BLOCK_COMMANDS:
            with self.subTest(command=name):
                text = _read(name)
                self.assertIn(
                    "VAULT_NAME",
                    text,
                    msg=f"{name}.md bash block must extract VAULT_NAME from $ARGUMENTS",
                )

    def test_bash_block_commands_resolve_via_config_loader(self):
        # Each must use config_loader.get_vault to resolve VAULT_PATH
        for name in self.BASH_BLOCK_COMMANDS:
            with self.subTest(command=name):
                text = _read(name)
                self.assertIn(
                    "config_loader",
                    text,
                    msg=f"{name}.md must resolve vault via config_loader (R-6.2/R-6.3)",
                )

    def test_legacy_vault_path_lookup_removed(self):
        # The old `s.startswith('vault_path')` lookup must be gone — it parses
        # the legacy schema and would break post-migration.
        for name in self.BASH_BLOCK_COMMANDS:
            with self.subTest(command=name):
                text = _read(name)
                self.assertNotIn(
                    "s.startswith('vault_path')",
                    text,
                    msg=f"{name}.md still uses legacy vault_path lookup; must use config_loader",
                )


class TestVaultIndependentCommandsUnchanged(unittest.TestCase):
    """R-6.5 — sq-chunk and sq-estimate stay vault-independent."""

    def test_chunk_does_not_mention_vault(self):
        text = _read("sq-chunk")
        self.assertNotIn("--vault", text)
        self.assertNotIn("VAULT_NAME", text)

    def test_estimate_does_not_mention_vault(self):
        text = _read("sq-estimate")
        self.assertNotIn("--vault", text)
        self.assertNotIn("VAULT_NAME", text)


if __name__ == "__main__":
    unittest.main()
