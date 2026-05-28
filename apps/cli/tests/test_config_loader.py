#!/usr/bin/env python3
"""
test_config_loader.py — Tests for lib/config_loader.py (story 1.2 — read API).

Covers EARS R-3.1 through R-3.6, R-3.13, R-3.14. Migration (R-2.x) and write
API (R-3.7 through R-3.12) are tested by separate stories (1.3, 1.4).
"""

import os
import pathlib
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

_LIB = pathlib.Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(_LIB))

import config_loader  # noqa: E402
from config_loader import (  # noqa: E402
    ConfigError,
    NoVaultsConfiguredError,
    ValidationError,
    Vault,
    VaultNotFoundError,
    _fallback_parse,
    add_vault,
    get_default_vault,
    get_vault,
    list_vaults,
    migrate_legacy,
    read_state,
    remove_vault,
    set_default,
    state_file_for,
    write_state,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


CONFIG_TWO_VAULTS = """\
default_email = "user@example.com"
machine_environment = "personal"

[[vaults]]
name = "personal"
path = "~/vault-tdah"
default = true

[[vaults]]
name = "work"
path = "/abs/work-vault"
default = false

[projects]
active = ["A", "B"]

[compliance]
strict = false
"""


CONFIG_ONE_VAULT = """\
default_email = "u@example.com"
machine_environment = "personal"

[[vaults]]
name = "only"
path = "~/v"
default = true
"""


def _write_tmp_config(text: str) -> pathlib.Path:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False, encoding="utf-8"
    )
    f.write(text)
    f.close()
    return pathlib.Path(f.name)


# ─── R-3.2: list_vaults ──────────────────────────────────────────────────────


class TestListVaults(unittest.TestCase):

    def test_returns_all_vaults_in_order(self):
        path = _write_tmp_config(CONFIG_TWO_VAULTS)
        try:
            vs = list_vaults(config_path=path)
            self.assertEqual(len(vs), 2)
            self.assertEqual(vs[0].name, "personal")
            self.assertEqual(vs[1].name, "work")
            self.assertTrue(vs[0].default)
            self.assertFalse(vs[1].default)
        finally:
            path.unlink()

    def test_expands_tilde_in_path(self):
        path = _write_tmp_config(CONFIG_TWO_VAULTS)
        try:
            vs = list_vaults(config_path=path)
            self.assertNotIn("~", str(vs[0].path))
            self.assertTrue(str(vs[0].path).startswith(str(pathlib.Path.home())))
        finally:
            path.unlink()

    def test_preserves_absolute_path(self):
        path = _write_tmp_config(CONFIG_TWO_VAULTS)
        try:
            vs = list_vaults(config_path=path)
            self.assertEqual(str(vs[1].path), "/abs/work-vault")
        finally:
            path.unlink()


# ─── R-3.3, R-3.4, R-3.5: get_vault ──────────────────────────────────────────


class TestGetVault(unittest.TestCase):

    def setUp(self):
        self.path = _write_tmp_config(CONFIG_TWO_VAULTS)

    def tearDown(self):
        self.path.unlink()

    def test_by_name_returns_match(self):
        v = get_vault(name="work", config_path=self.path)
        self.assertIsInstance(v, Vault)
        self.assertEqual(v.name, "work")

    def test_no_name_returns_default(self):
        v = get_vault(config_path=self.path)
        self.assertEqual(v.name, "personal")
        self.assertTrue(v.default)

    def test_unknown_name_raises_with_helpful_message(self):
        with self.assertRaises(VaultNotFoundError) as ctx:
            get_vault(name="missing", config_path=self.path)
        msg = str(ctx.exception)
        self.assertIn("missing", msg)
        self.assertIn("personal", msg)
        self.assertIn("work", msg)


# ─── R-3.6: get_default_vault ────────────────────────────────────────────────


class TestGetDefaultVault(unittest.TestCase):

    def test_returns_default(self):
        path = _write_tmp_config(CONFIG_ONE_VAULT)
        try:
            v = get_default_vault(config_path=path)
            self.assertEqual(v.name, "only")
            self.assertTrue(v.default)
        finally:
            path.unlink()


# ─── R-1.x schema validation surfaced by load ────────────────────────────────


class TestSchemaValidation(unittest.TestCase):

    def test_zero_defaults_raises(self):
        bad = textwrap.dedent("""\
            [[vaults]]
            name = "a"
            path = "/tmp/a"
            default = false
        """)
        path = _write_tmp_config(bad)
        try:
            with self.assertRaises(ConfigError) as ctx:
                list_vaults(config_path=path)
            self.assertIn("default", str(ctx.exception))
        finally:
            path.unlink()

    def test_two_defaults_raises(self):
        bad = textwrap.dedent("""\
            [[vaults]]
            name = "a"
            path = "/tmp/a"
            default = true

            [[vaults]]
            name = "b"
            path = "/tmp/b"
            default = true
        """)
        path = _write_tmp_config(bad)
        try:
            with self.assertRaises(ConfigError) as ctx:
                list_vaults(config_path=path)
            self.assertIn("2", str(ctx.exception))
        finally:
            path.unlink()

    def test_duplicate_name_raises(self):
        bad = textwrap.dedent("""\
            [[vaults]]
            name = "dup"
            path = "/tmp/a"
            default = true

            [[vaults]]
            name = "dup"
            path = "/tmp/b"
            default = false
        """)
        path = _write_tmp_config(bad)
        try:
            with self.assertRaises(ConfigError) as ctx:
                list_vaults(config_path=path)
            self.assertIn("duplicate", str(ctx.exception).lower())
        finally:
            path.unlink()

    def test_missing_name_raises(self):
        bad = textwrap.dedent("""\
            [[vaults]]
            path = "/tmp/a"
            default = true
        """)
        path = _write_tmp_config(bad)
        try:
            with self.assertRaises(ConfigError):
                list_vaults(config_path=path)
        finally:
            path.unlink()

    def test_missing_path_raises(self):
        bad = textwrap.dedent("""\
            [[vaults]]
            name = "a"
            default = true
        """)
        path = _write_tmp_config(bad)
        try:
            with self.assertRaises(ConfigError):
                list_vaults(config_path=path)
        finally:
            path.unlink()

    def test_empty_vaults_array_raises(self):
        # File with no [[vaults]] and no legacy fields
        bad = """default_email = "u@x"\n"""
        path = _write_tmp_config(bad)
        try:
            with self.assertRaises(NoVaultsConfiguredError):
                list_vaults(config_path=path)
        finally:
            path.unlink()

    def test_legacy_vault_path_auto_migrates_on_load(self):
        # Story 1.4: migration runs lazily, returns migrated vaults seamlessly.
        legacy = textwrap.dedent("""\
            vault_path = "/tmp"
            environment_name = "personal"
        """)
        path = _write_tmp_config(legacy)
        try:
            vs = list_vaults(config_path=path)
            self.assertEqual(len(vs), 1)
            self.assertEqual(vs[0].name, "personal")
            self.assertTrue(vs[0].default)
            # File on disk has been rewritten
            new_text = path.read_text()
            self.assertIn("[[vaults]]", new_text)
            self.assertIn("# Auto-migrated", new_text)
            self.assertNotIn("vault_path", new_text)
            self.assertIn("machine_environment", new_text)
        finally:
            path.unlink()

    def test_missing_file_raises(self):
        with self.assertRaises(NoVaultsConfiguredError):
            list_vaults(config_path=pathlib.Path("/nonexistent/path/config.toml"))


# ─── R-3.13: state_file_for ──────────────────────────────────────────────────


class TestStateFileFor(unittest.TestCase):

    def test_returns_expected_path_and_creates_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp) / "state"
            self.assertFalse(base.exists())
            p = state_file_for("personal", state_dir=base)
            self.assertTrue(base.exists())
            self.assertEqual(p, base / "personal.json")

    def test_idempotent_when_parent_already_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp) / "state"
            state_file_for("v1", state_dir=base)
            # Second call must not raise
            state_file_for("v2", state_dir=base)
            self.assertTrue((base / "v1.json").parent.exists())


# ─── R-3.14: TOML parser — tomllib + fallback equivalence ────────────────────


class TestFallbackParserEquivalence(unittest.TestCase):
    """The fallback parser must produce equivalent output to tomllib for our schema."""

    def test_fallback_matches_tomllib_on_full_config(self):
        if sys.version_info < (3, 11):
            self.skipTest("tomllib not available below 3.11")
        import tomllib
        parsed_tomllib = tomllib.loads(CONFIG_TWO_VAULTS)
        parsed_fallback = _fallback_parse(CONFIG_TWO_VAULTS)
        # Compare structurally (both should produce the same dict shape)
        self.assertEqual(parsed_tomllib.keys(), parsed_fallback.keys())
        self.assertEqual(len(parsed_tomllib["vaults"]), len(parsed_fallback["vaults"]))
        for tv, fv in zip(parsed_tomllib["vaults"], parsed_fallback["vaults"]):
            self.assertEqual(tv["name"], fv["name"])
            self.assertEqual(tv["path"], fv["path"])
            self.assertEqual(tv["default"], fv["default"])

    def test_fallback_handles_comments_inside_strings(self):
        text = 'key = "value with # hash inside"\n'
        parsed = _fallback_parse(text)
        self.assertEqual(parsed["key"], "value with # hash inside")

    def test_fallback_handles_trailing_comments(self):
        text = 'key = "value"  # trailing comment\n'
        parsed = _fallback_parse(text)
        self.assertEqual(parsed["key"], "value")

    def test_fallback_handles_inline_string_array(self):
        text = 'tags = ["a", "b", "c"]\n'
        parsed = _fallback_parse(text)
        self.assertEqual(parsed["tags"], ["a", "b", "c"])

    def test_fallback_handles_empty_array(self):
        text = "empty = []\n"
        parsed = _fallback_parse(text)
        self.assertEqual(parsed["empty"], [])

    def test_fallback_handles_booleans(self):
        text = "yes = true\nno = false\n"
        parsed = _fallback_parse(text)
        self.assertIs(parsed["yes"], True)
        self.assertIs(parsed["no"], False)

    def test_using_fallback_via_mocked_tomllib_import(self):
        """Force the loader to use the fallback by simulating Python < 3.11."""
        path = _write_tmp_config(CONFIG_TWO_VAULTS)
        try:
            # Simulate Python 3.10 by patching version_info to (3, 10, ...)
            with mock.patch.object(config_loader.sys, "version_info", (3, 10, 0, "final", 0)):
                vs = list_vaults(config_path=path)
            self.assertEqual(len(vs), 2)
            self.assertEqual(vs[0].name, "personal")
        finally:
            path.unlink()


# ─── R-3.1: module surface ───────────────────────────────────────────────────


class TestPublicApiSurface(unittest.TestCase):

    def test_exports_required_functions(self):
        required = ("list_vaults", "get_vault", "get_default_vault", "state_file_for")
        for name in required:
            self.assertTrue(hasattr(config_loader, name), f"missing {name}")

    def test_exports_exception_classes(self):
        self.assertTrue(issubclass(VaultNotFoundError, ConfigError))
        self.assertTrue(issubclass(NoVaultsConfiguredError, ConfigError))


# ─── R-3.7, R-3.8: add_vault ─────────────────────────────────────────────────


class TestAddVault(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp.name)
        # Two real directories we can register as vault paths
        self.vault_a = self.tmp_path / "vault-a"
        self.vault_b = self.tmp_path / "vault-b"
        self.vault_a.mkdir()
        self.vault_b.mkdir()
        # A file (not directory) to test rejection
        self.not_a_dir = self.tmp_path / "regular-file.txt"
        self.not_a_dir.write_text("nope")
        self.cfg_path = self.tmp_path / "config.toml"

    def tearDown(self):
        self.tmp.cleanup()

    def test_bootstrap_creates_file_with_default_true(self):
        self.assertFalse(self.cfg_path.exists())
        v = add_vault("first", str(self.vault_a), config_path=self.cfg_path)
        self.assertEqual(v.name, "first")
        self.assertTrue(v.default)
        # File is now valid
        vs = list_vaults(config_path=self.cfg_path)
        self.assertEqual(len(vs), 1)
        self.assertTrue(vs[0].default)

    def test_second_add_creates_with_default_false(self):
        add_vault("first", str(self.vault_a), config_path=self.cfg_path)
        v = add_vault("second", str(self.vault_b), config_path=self.cfg_path)
        self.assertFalse(v.default)
        vs = list_vaults(config_path=self.cfg_path)
        self.assertEqual(len(vs), 2)
        # First entry preserved as default
        self.assertEqual(vs[0].name, "first")
        self.assertTrue(vs[0].default)

    def test_rejects_duplicate_name(self):
        add_vault("dup", str(self.vault_a), config_path=self.cfg_path)
        with self.assertRaises(ValidationError) as ctx:
            add_vault("dup", str(self.vault_b), config_path=self.cfg_path)
        self.assertIn("already exists", str(ctx.exception))

    def test_rejects_missing_path(self):
        with self.assertRaises(ValidationError) as ctx:
            add_vault(
                "bad",
                str(self.tmp_path / "no-such-dir"),
                config_path=self.cfg_path,
            )
        self.assertIn("does not exist", str(ctx.exception))

    def test_rejects_path_that_is_file(self):
        with self.assertRaises(ValidationError) as ctx:
            add_vault("bad", str(self.not_a_dir), config_path=self.cfg_path)
        self.assertIn("not a directory", str(ctx.exception))

    def test_rejects_empty_name(self):
        with self.assertRaises(ValidationError):
            add_vault("", str(self.vault_a), config_path=self.cfg_path)

    def test_preserves_existing_comments_and_sections(self):
        existing = textwrap.dedent("""\
            # User's hand-written comment
            default_email = "u@x"
            machine_environment = "personal"

            [[vaults]]
            name = "personal"
            path = "{}"
            default = true

            [compliance]
            strict = false
        """).format(self.vault_a)
        self.cfg_path.write_text(existing)
        add_vault("work", str(self.vault_b), config_path=self.cfg_path)
        new_text = self.cfg_path.read_text()
        self.assertIn("# User's hand-written comment", new_text)
        self.assertIn("[compliance]", new_text)
        self.assertIn("default_email", new_text)
        self.assertIn('name = "personal"', new_text)
        self.assertIn('name = "work"', new_text)
        # Verify the final state is loadable and correct
        vs = list_vaults(config_path=self.cfg_path)
        self.assertEqual([v.name for v in vs], ["personal", "work"])
        self.assertTrue(vs[0].default)
        self.assertFalse(vs[1].default)


# ─── R-3.9, R-3.10: remove_vault ─────────────────────────────────────────────


class TestRemoveVault(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp.name)
        self.vault_a = self.tmp_path / "a"
        self.vault_b = self.tmp_path / "b"
        self.vault_a.mkdir()
        self.vault_b.mkdir()
        self.cfg_path = self.tmp_path / "config.toml"
        add_vault("a", str(self.vault_a), config_path=self.cfg_path)
        add_vault("b", str(self.vault_b), config_path=self.cfg_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_removes_non_default(self):
        remove_vault("b", config_path=self.cfg_path)
        vs = list_vaults(config_path=self.cfg_path)
        self.assertEqual([v.name for v in vs], ["a"])

    def test_refuses_to_remove_default(self):
        with self.assertRaises(ValidationError) as ctx:
            remove_vault("a", config_path=self.cfg_path)
        msg = str(ctx.exception)
        self.assertIn("default", msg)
        self.assertIn("b", msg)  # hints at the other vault

    def test_unknown_name_raises(self):
        with self.assertRaises(VaultNotFoundError):
            remove_vault("missing", config_path=self.cfg_path)

    def test_removal_preserves_other_sections(self):
        # Hand-edit to add a [compliance] section
        text = self.cfg_path.read_text()
        text += '\n[compliance]\nstrict = true\n'
        self.cfg_path.write_text(text)
        remove_vault("b", config_path=self.cfg_path)
        new_text = self.cfg_path.read_text()
        self.assertIn("[compliance]", new_text)
        self.assertIn("strict = true", new_text)


# ─── R-3.11, R-3.12: set_default ─────────────────────────────────────────────


class TestSetDefault(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp.name)
        self.vault_a = self.tmp_path / "a"
        self.vault_b = self.tmp_path / "b"
        self.vault_c = self.tmp_path / "c"
        for d in (self.vault_a, self.vault_b, self.vault_c):
            d.mkdir()
        self.cfg_path = self.tmp_path / "config.toml"
        add_vault("a", str(self.vault_a), config_path=self.cfg_path)
        add_vault("b", str(self.vault_b), config_path=self.cfg_path)
        add_vault("c", str(self.vault_c), config_path=self.cfg_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sets_new_default(self):
        # Initially "a" is default
        self.assertEqual(get_default_vault(config_path=self.cfg_path).name, "a")
        set_default("c", config_path=self.cfg_path)
        self.assertEqual(get_default_vault(config_path=self.cfg_path).name, "c")
        # Verify exactly one default
        vs = list_vaults(config_path=self.cfg_path)
        defaults = [v for v in vs if v.default]
        self.assertEqual(len(defaults), 1)
        self.assertEqual(defaults[0].name, "c")

    def test_set_to_current_default_is_idempotent(self):
        set_default("a", config_path=self.cfg_path)
        self.assertEqual(get_default_vault(config_path=self.cfg_path).name, "a")

    def test_unknown_name_raises(self):
        with self.assertRaises(VaultNotFoundError):
            set_default("zzz", config_path=self.cfg_path)


# ─── Atomic write & no temp file left behind ─────────────────────────────────


class TestAtomicWrites(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp.name)
        self.vault_a = self.tmp_path / "a"
        self.vault_b = self.tmp_path / "b"
        self.vault_a.mkdir()
        self.vault_b.mkdir()
        self.cfg_path = self.tmp_path / "config.toml"

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_tmp_file_left_behind_after_add(self):
        add_vault("a", str(self.vault_a), config_path=self.cfg_path)
        siblings = list(self.cfg_path.parent.glob("config.toml*"))
        self.assertEqual(
            sorted(s.name for s in siblings), ["config.toml"]
        )

    def test_no_tmp_file_left_behind_after_remove(self):
        add_vault("a", str(self.vault_a), config_path=self.cfg_path)
        add_vault("b", str(self.vault_b), config_path=self.cfg_path)
        remove_vault("b", config_path=self.cfg_path)
        siblings = list(self.cfg_path.parent.glob("config.toml*"))
        self.assertEqual(
            sorted(s.name for s in siblings), ["config.toml"]
        )

    def test_no_tmp_file_left_behind_after_set_default(self):
        add_vault("a", str(self.vault_a), config_path=self.cfg_path)
        add_vault("b", str(self.vault_b), config_path=self.cfg_path)
        set_default("b", config_path=self.cfg_path)
        siblings = list(self.cfg_path.parent.glob("config.toml*"))
        self.assertEqual(
            sorted(s.name for s in siblings), ["config.toml"]
        )


# ─── R-2.x: migration ────────────────────────────────────────────────────────


class TestMigration(unittest.TestCase):
    """Story 1.4 — lazy migration of legacy single-vault configs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp.name)
        self.cfg_path = self.tmp_path / "config.toml"
        self.state_dir = self.tmp_path / "state"

    def tearDown(self):
        self.tmp.cleanup()

    def test_migrates_basic_legacy(self):
        # R-2.1, R-2.2, R-2.6
        self.cfg_path.write_text(textwrap.dedent("""\
            vault_path = "/tmp"
            environment_name = "personal"
            default_email = "u@x"
        """))
        ran = migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        self.assertTrue(ran)
        new_text = self.cfg_path.read_text()
        # R-2.6: auto-migrated comment on line 1
        self.assertTrue(new_text.splitlines()[0].startswith("# Auto-migrated"))
        # R-2.4: vault_path removed
        self.assertNotIn("vault_path", new_text)
        # R-2.5: environment_name renamed to machine_environment
        self.assertNotIn("environment_name", new_text)
        self.assertIn('machine_environment = "personal"', new_text)
        # R-2.2: new [[vaults]] with default = true
        self.assertIn("[[vaults]]", new_text)
        self.assertIn('name = "personal"', new_text)
        self.assertIn('path = "/tmp"', new_text)
        self.assertIn("default = true", new_text)

    def test_preserves_other_sections_and_comments(self):
        # R-2.3
        self.cfg_path.write_text(textwrap.dedent("""\
            # My personal config — please don't touch
            vault_path = "/tmp"
            environment_name = "personal"
            default_email = "u@x"

            [projects]
            active = ["A", "B"]

            [compliance]
            strict = false
        """))
        migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        new_text = self.cfg_path.read_text()
        self.assertIn("# My personal config", new_text)
        self.assertIn("[projects]", new_text)
        self.assertIn('active = ["A", "B"]', new_text)
        self.assertIn("[compliance]", new_text)
        self.assertIn("strict = false", new_text)

    def test_inserts_vaults_before_first_section(self):
        # New [[vaults]] block sits between scalars and [section] blocks
        self.cfg_path.write_text(textwrap.dedent("""\
            vault_path = "/tmp"
            environment_name = "personal"

            [compliance]
            strict = false
        """))
        migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        new_text = self.cfg_path.read_text()
        vaults_pos = new_text.find("[[vaults]]")
        compliance_pos = new_text.find("[compliance]")
        self.assertGreater(vaults_pos, 0)
        self.assertGreater(compliance_pos, vaults_pos)

    def test_idempotent(self):
        # R-2.11
        self.cfg_path.write_text(textwrap.dedent("""\
            vault_path = "/tmp"
            environment_name = "personal"
        """))
        ran1 = migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        text_after_first = self.cfg_path.read_text()
        ran2 = migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        text_after_second = self.cfg_path.read_text()
        self.assertTrue(ran1)
        self.assertFalse(ran2)
        self.assertEqual(text_after_first, text_after_second)
        # Verify the comment was not duplicated
        self.assertEqual(
            text_after_second.count("# Auto-migrated"), 1
        )

    def test_no_op_when_already_migrated(self):
        # R-2.8
        self.cfg_path.write_text(textwrap.dedent("""\
            [[vaults]]
            name = "a"
            path = "/tmp"
            default = true
        """))
        ran = migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        self.assertFalse(ran)

    def test_no_op_when_no_legacy_and_no_vaults(self):
        # R-2.9
        self.cfg_path.write_text('default_email = "u@x"\n')
        ran = migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        self.assertFalse(ran)

    def test_no_op_when_file_missing(self):
        # R-2.1 implies migration is gated on file presence
        ran = migrate_legacy(
            config_path=self.tmp_path / "nope.toml",
            state_dir=self.state_dir,
        )
        self.assertFalse(ran)

    def test_legacy_without_environment_name_defaults_to_default(self):
        self.cfg_path.write_text('vault_path = "/tmp"\n')
        migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        vs = list_vaults(config_path=self.cfg_path)
        self.assertEqual(vs[0].name, "default")

    def test_moves_legacy_state_file(self):
        # R-2.10
        self.cfg_path.write_text(textwrap.dedent("""\
            vault_path = "/tmp"
            environment_name = "personal"
        """))
        # Place a legacy state.json next to where the new state/ dir will live
        legacy_state = self.state_dir.parent / "state.json"
        legacy_state.parent.mkdir(parents=True, exist_ok=True)
        legacy_state.write_text('{"current_project": "X"}')
        migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        # Legacy file should be moved
        self.assertFalse(legacy_state.exists())
        self.assertTrue((self.state_dir / "personal.json").exists())
        self.assertEqual(
            (self.state_dir / "personal.json").read_text(),
            '{"current_project": "X"}',
        )

    def test_re_migrates_after_legacy_revert(self):
        # R-9.3: if user reverts to legacy form, migration runs again
        self.cfg_path.write_text(textwrap.dedent("""\
            vault_path = "/tmp"
            environment_name = "personal"
        """))
        migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        # User manually overwrites with legacy form again
        self.cfg_path.write_text(textwrap.dedent("""\
            vault_path = "/tmp"
            environment_name = "work"
        """))
        ran = migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        self.assertTrue(ran)
        vs = list_vaults(config_path=self.cfg_path)
        self.assertEqual(vs[0].name, "work")

    def test_list_vaults_transparently_migrates(self):
        # Migration is lazy on load via list_vaults
        self.cfg_path.write_text(textwrap.dedent("""\
            vault_path = "/tmp"
            environment_name = "personal"
        """))
        vs = list_vaults(config_path=self.cfg_path)
        self.assertEqual(vs[0].name, "personal")
        # Confirm the file was rewritten
        self.assertIn("[[vaults]]", self.cfg_path.read_text())

    def test_atomic_no_temp_file_after_migration(self):
        self.cfg_path.write_text('vault_path = "/tmp"\n')
        migrate_legacy(config_path=self.cfg_path, state_dir=self.state_dir)
        siblings = list(self.cfg_path.parent.glob("config.toml*"))
        self.assertEqual(sorted(s.name for s in siblings), ["config.toml"])


# ─── R-8.x: per-vault state files ────────────────────────────────────────────


class TestPerVaultState(unittest.TestCase):
    """Story 1.5 — per-vault state file convention."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_dir = pathlib.Path(self.tmp.name) / "state"

    def tearDown(self):
        self.tmp.cleanup()

    def test_read_missing_returns_empty(self):
        data = read_state("nonexistent", state_dir=self.state_dir)
        self.assertEqual(data, {})

    def test_write_then_read_roundtrips(self):
        # R-8.4 — preserves the canonical schema
        payload = {
            "current_project": "PROJ-A",
            "current_intent": "PROJ-A-INTENT-001",
            "last_switch_at": "2026-05-25T12:00:00Z",
            "switch_ledger": [
                {"from": None, "to": "PROJ-A", "reason": "session-start"},
            ],
        }
        write_state("personal", payload, state_dir=self.state_dir)
        out = read_state("personal", state_dir=self.state_dir)
        self.assertEqual(out, payload)

    def test_separate_vaults_dont_collide(self):
        # R-8.1 — per-vault isolation
        write_state("personal", {"current_project": "PERSONAL-A"}, state_dir=self.state_dir)
        write_state("work", {"current_project": "WORK-X"}, state_dir=self.state_dir)
        self.assertEqual(
            read_state("personal", state_dir=self.state_dir)["current_project"],
            "PERSONAL-A",
        )
        self.assertEqual(
            read_state("work", state_dir=self.state_dir)["current_project"],
            "WORK-X",
        )

    def test_write_is_atomic_no_temp_file(self):
        # R-8.3 — atomic write
        write_state("v1", {"x": 1}, state_dir=self.state_dir)
        siblings = list(self.state_dir.glob("v1.json*"))
        self.assertEqual(sorted(s.name for s in siblings), ["v1.json"])

    def test_corrupt_state_file_yields_empty_dict(self):
        # Robustness: a hand-edited bad JSON shouldn't crash callers
        p = state_file_for("v1", state_dir=self.state_dir)
        p.write_text("{not valid json")
        self.assertEqual(read_state("v1", state_dir=self.state_dir), {})

    def test_write_creates_parent_dir(self):
        # state_file_for guarantees parent exists
        nested = pathlib.Path(self.tmp.name) / "nested" / "deeper" / "state"
        write_state("v1", {"k": "v"}, state_dir=nested)
        self.assertTrue((nested / "v1.json").exists())

    def test_write_state_preserves_unknown_keys(self):
        # Future-proofing — callers can add custom keys
        payload = {
            "current_project": "X",
            "custom_extension_field": {"hello": "world"},
        }
        write_state("v1", payload, state_dir=self.state_dir)
        out = read_state("v1", state_dir=self.state_dir)
        self.assertEqual(out["custom_extension_field"], {"hello": "world"})


# ─── Public API surface for writes ───────────────────────────────────────────


class TestWriteApiSurface(unittest.TestCase):

    def test_exports_required_functions(self):
        for name in ("add_vault", "remove_vault", "set_default"):
            self.assertTrue(hasattr(config_loader, name), f"missing {name}")

    def test_exports_validation_error(self):
        self.assertTrue(issubclass(ValidationError, ConfigError))


if __name__ == "__main__":
    unittest.main()
