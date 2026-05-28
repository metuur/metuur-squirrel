#!/usr/bin/env python3
"""
Story 4.1 — verify every vault-touching SKILL.md forwards vault_name.

Acceptance (from docs/ears/multi-vault-core.md):
  R-7.1: update the frontmatter of every skills/*/SKILL.md whose body invokes
         lib/ scripts that touch the vault to document an optional vault_name
         argument.
  R-7.2: WHEN a skill receives a vault_name argument, THE SYSTEM SHALL pass
         --vault $vault_name to every python3 lib/... call in the skill body.
  R-7.3: WHEN a skill receives no vault_name, THE SYSTEM SHALL omit the flag,
         deferring to config_loader.get_default_vault().

Verify (from docs/tasks/multi-vault-core.md story 4.1):
  every skills/*/SKILL.md whose body invokes a vault-touching lib/*.py script
  declares vault_name as an optional argument in its frontmatter description
  and forwards --vault $vault_name when present.

Audit list (full): capture, brief, decision, session-start, session-end,
sync-in, sync-out, where-am-i, recover, parakeet, chunk-intent, task-initiation.

Sub-classification of the audit list:

  SCRIPT_VAULT_SKILLS:
    Invoke python3 lib/*.py with --vault (or python3 -c block that resolves
    vault). MUST declare vault_name in frontmatter AND forward --vault when
    vault_name is present.
      brief, parakeet, recover, session-start, where-am-i

  READ_WRITE_VAULT_SKILLS:
    Touch vault files via Read/Write/shell but do not run vault-touching
    python3 lib/*.py scripts. MUST declare vault_name in frontmatter so the
    user can scope the skill to a specific vault.
      capture, decision, session-end, sync-in, sync-out, task-initiation

  VAULT_INDEPENDENT_SKILLS:
    Operate on data the user provides; do not touch any vault. MUST NOT
    mention vault_name.
      chunk-intent
"""

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "skills"

SCRIPT_VAULT_SKILLS = [
    "brief",
    "parakeet",
    "recover",
    "session-start",
    "where-am-i",
]

READ_WRITE_VAULT_SKILLS = [
    "capture",
    "decision",
    "session-end",
    "sync-in",
    "sync-out",
    "task-initiation",
]

VAULT_INDEPENDENT_SKILLS = ["chunk-intent"]


def _read(name: str) -> str:
    p = SKILLS_DIR / name / "SKILL.md"
    assert p.exists(), f"missing skill file: {p}"
    return p.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    """Return the YAML frontmatter block as a string (between the first two `---`)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert m, "skill file must start with a YAML frontmatter block"
    return m.group(1)


class TestScriptVaultSkillsDeclareVaultName(unittest.TestCase):
    """R-7.1 — skills invoking vault-touching lib scripts document vault_name."""

    def test_all_script_vault_skills_mention_vault_name_in_frontmatter(self):
        for name in SCRIPT_VAULT_SKILLS:
            with self.subTest(skill=name):
                fm = _frontmatter(_read(name))
                self.assertIn(
                    "vault_name",
                    fm,
                    msg=(
                        f"skills/{name}/SKILL.md frontmatter must document "
                        f"optional vault_name argument (R-7.1)"
                    ),
                )


class TestScriptVaultSkillsForwardVaultFlag(unittest.TestCase):
    """R-7.2 — when vault_name is present, the vault selection is forwarded.

    The lib scripts (status_aggregator, deadline_scanner, session_scanner,
    switch_tracker) take a vault PATH via --vault, not a name. So the skill
    body resolves vault_name -> path via config_loader.get_vault and then
    passes --vault "$VAULT" downstream. This matches the slash-command idiom
    in sq-status.md (R-6.2 implementation).
    """

    def test_all_script_vault_skills_thread_vault_name_through_config_loader(self):
        # The body must:
        #   (a) reference $vault_name (the optional skill argument), AND
        #   (b) call config_loader.get_vault(name=...) — passing either
        #       vault_name directly or a local that was assigned from it.
        # When vault_name is set, the named vault is resolved; when unset,
        # get_vault(name=None) returns the default vault (R-7.3).
        name_ref = re.compile(r"\$\{?vault_name\}?")
        get_vault_call = re.compile(r"get_vault\s*\(\s*name\s*=")
        for name in SCRIPT_VAULT_SKILLS:
            with self.subTest(skill=name):
                text = _read(name)
                self.assertRegex(
                    text,
                    name_ref,
                    msg=(
                        f"skills/{name}/SKILL.md body must reference "
                        f"$vault_name (the optional skill argument) (R-7.2)"
                    ),
                )
                self.assertRegex(
                    text,
                    get_vault_call,
                    msg=(
                        f"skills/{name}/SKILL.md body must call "
                        f"config_loader.get_vault(name=...) so vault_name "
                        f"routes to the right vault and absence routes to "
                        f"the default (R-7.2, R-7.3)"
                    ),
                )


class TestScriptVaultSkillsResolveViaConfigLoader(unittest.TestCase):
    """R-7.3 — when no vault_name is provided, fall back to config_loader."""

    def test_all_script_vault_skills_reference_config_loader(self):
        # The skill should resolve the vault path via config_loader (which
        # picks the default vault when no name is given). Loose check: file
        # mentions config_loader somewhere in its workflow.
        for name in SCRIPT_VAULT_SKILLS:
            with self.subTest(skill=name):
                text = _read(name)
                self.assertIn(
                    "config_loader",
                    text,
                    msg=(
                        f"skills/{name}/SKILL.md must resolve vault via "
                        f"config_loader so omitting vault_name picks the "
                        f"default (R-7.3)"
                    ),
                )

    def test_legacy_vault_path_lookup_removed_in_script_vault_skills(self):
        # The legacy single-vault lookup must not survive — it parses the old
        # schema and would break post-migration.
        for name in SCRIPT_VAULT_SKILLS:
            with self.subTest(skill=name):
                text = _read(name)
                self.assertNotIn(
                    "s.startswith('vault_path')",
                    text,
                    msg=(
                        f"skills/{name}/SKILL.md still uses the legacy "
                        f"vault_path lookup; switch to config_loader"
                    ),
                )


class TestReadWriteVaultSkillsDeclareVaultName(unittest.TestCase):
    """R-7.1 (extended audit) — vault-touching read/write skills also expose vault_name."""

    def test_all_read_write_vault_skills_mention_vault_name(self):
        for name in READ_WRITE_VAULT_SKILLS:
            with self.subTest(skill=name):
                fm = _frontmatter(_read(name))
                self.assertIn(
                    "vault_name",
                    fm,
                    msg=(
                        f"skills/{name}/SKILL.md frontmatter must document "
                        f"optional vault_name (R-7.1 audit list)"
                    ),
                )


class TestVaultIndependentSkillsUnchanged(unittest.TestCase):
    """chunk-intent operates on user-provided estimates; no vault involved."""

    def test_chunk_intent_does_not_mention_vault_name(self):
        for name in VAULT_INDEPENDENT_SKILLS:
            with self.subTest(skill=name):
                text = _read(name)
                self.assertNotIn(
                    "vault_name",
                    text,
                    msg=(
                        f"skills/{name}/SKILL.md is vault-independent and "
                        f"must NOT reference vault_name"
                    ),
                )


if __name__ == "__main__":
    unittest.main()
