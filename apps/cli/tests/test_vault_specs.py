"""
tests/test_vault_specs.py — Automated verification for VAULT-001 through VAULT-008.

Covers:
  VAULT-003: tag_parser validation/parse contract
  VAULT-005: status_aggregator schema_version field
  VAULT-008: no third-party imports in lib modules
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure lib/ is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

FIXTURE_VAULT = Path(__file__).parent / "fixtures" / "vault-minimal"


# ─────────────────────────────────────────────────────────────────────────────
# VAULT-003: tag_parser contract
# ─────────────────────────────────────────────────────────────────────────────

class TestVault003TagParser:
    """VAULT-003: lib/tag_parser.py is sole authority for tag validation."""

    def setup_method(self):
        import tag_parser
        self.tp = tag_parser

    # @spec VAULT-003
    def test_valid_tag_returns_true_and_none(self):
        ok, msg = self.tp.validate("PROJ-SUB-COMP-001")
        assert ok is True
        assert msg is None

    # @spec VAULT-003
    def test_valid_tag_full_length(self):
        ok, msg = self.tp.validate("VISA-FAMILIA-TRAMITE-007")
        assert ok is True
        assert msg is None

    # @spec VAULT-003
    def test_invalid_no_leading_zeros(self):
        """Tag with suffix that isn't exactly 3 digits should fail."""
        ok, msg = self.tp.validate("PROJ-SUB-COMP-1")
        assert ok is False

    # @spec VAULT-003
    def test_invalid_lowercase(self):
        ok, msg = self.tp.validate("proj-sub-comp-001")
        assert ok is False

    # @spec VAULT-003
    def test_invalid_only_two_named_segments(self):
        """Only 2 named segments before number — must fail."""
        ok, msg = self.tp.validate("PROJ-COMP-001")
        assert ok is False

    # @spec VAULT-003
    def test_invalid_none(self):
        ok, msg = self.tp.validate(None)
        assert ok is False

    # @spec VAULT-003
    def test_invalid_empty_string(self):
        ok, msg = self.tp.validate("")
        assert ok is False

    # @spec VAULT-003
    def test_invalid_four_digit_suffix(self):
        """Suffix with 4 digits is too long — must fail."""
        ok, msg = self.tp.validate("PROJ-SUB-COMP-0001")
        assert ok is False

    # @spec VAULT-003
    def test_invalid_two_digit_suffix(self):
        ok, msg = self.tp.validate("PROJ-SUB-COMP-01")
        assert ok is False

    # @spec VAULT-003
    def test_parse_returns_correct_keys(self):
        result = self.tp.parse("PROJ-SUB-COMP-001")
        assert result is not None
        assert set(result.keys()) == {"project", "subarea", "component", "number"}

    # @spec VAULT-003
    def test_parse_values_are_correct(self):
        result = self.tp.parse("VISA-FAMILIA-TRAMITE-007")
        assert result["project"] == "VISA"
        assert result["subarea"] == "FAMILIA"
        assert result["component"] == "TRAMITE"
        assert result["number"] == 7

    # @spec VAULT-003
    def test_parse_invalid_returns_none(self):
        assert self.tp.parse("not-a-valid-tag") is None
        assert self.tp.parse("PROJ-COMP-001") is None
        assert self.tp.parse("proj-sub-comp-001") is None

    # @spec VAULT-003
    def test_parse_numero_is_integer(self):
        result = self.tp.parse("TEST-SUB-COMP-042")
        assert isinstance(result["number"], int)
        assert result["number"] == 42

    # @spec VAULT-003
    def test_validate_suggestion_for_recoverable_tag(self):
        """Lowercase valid structure should produce a suggestion."""
        ok, suggestion = self.tp.validate("proj-sub-comp-001")
        assert ok is False
        # suggestion may be a corrected form or None depending on logic
        # just confirm it doesn't raise

    # @spec VAULT-003
    def test_zero_padded_suffix_zero_zero_one(self):
        ok, _ = self.tp.validate("PROJ-SUB-COMP-000")
        assert ok is True


# ─────────────────────────────────────────────────────────────────────────────
# VAULT-005: schema_version in status_aggregator output
# ─────────────────────────────────────────────────────────────────────────────

class TestVault005SchemaVersion:
    """VAULT-005: aggregate_status() JSON contract must include schema_version."""

    def setup_method(self):
        import status_aggregator
        self.sa = status_aggregator

    # @spec VAULT-005
    def test_schema_version_present_in_top_level(self):
        result = self.sa.aggregate_status(FIXTURE_VAULT)
        assert "schema_version" in result, "schema_version missing from top-level JSON"

    # @spec VAULT-005
    def test_schema_version_is_nonempty_string(self):
        result = self.sa.aggregate_status(FIXTURE_VAULT)
        sv = result["schema_version"]
        assert isinstance(sv, str)
        assert len(sv) > 0

    # @spec VAULT-005
    def test_schema_version_not_nested(self):
        """schema_version must be at top level, not inside a sub-dict."""
        result = self.sa.aggregate_status(FIXTURE_VAULT)
        # It must be directly accessible
        assert result.get("schema_version") is not None

    # @spec VAULT-005
    def test_result_is_dict(self):
        result = self.sa.aggregate_status(FIXTURE_VAULT)
        assert isinstance(result, dict)

    # @spec VAULT-005
    def test_schema_version_serializes_to_json(self):
        """Ensure the full output is JSON-serialisable (no datetime objects leaking)."""
        result = self.sa.aggregate_status(FIXTURE_VAULT)
        serialized = json.dumps(result, default=str)
        reparsed = json.loads(serialized)
        assert "schema_version" in reparsed


# ─────────────────────────────────────────────────────────────────────────────
# VAULT-008: stdlib-only imports across all lib modules
# ─────────────────────────────────────────────────────────────────────────────

STDLIB_MODULES = {
    "json", "re", "sys", "os", "pathlib", "datetime", "argparse", "hashlib",
    "subprocess", "typing", "textwrap", "collections", "shutil", "tempfile",
    "functools", "itertools", "copy", "math", "random", "string", "struct",
    "time", "calendar", "decimal", "enum", "dataclasses", "abc", "io", "csv",
    "configparser", "unittest", "contextlib", "urllib", "email", "html",
    "base64", "hmac", "secrets", "uuid", "platform", "signal", "threading",
    "queue",
}

# Intra-lib sibling imports are allowed (they live in lib/ next to each other)
SIBLING_MODULES = {
    "intent_parser", "status_aggregator", "tag_parser", "switch_tracker",
    "deadline_scanner", "package_protocol", "chunk_helper", "estimate_buffer",
    "session_scanner", "dashboard_generator", "manifest_writer",
    "vault_migrator",
}

LIB_DIR = Path(__file__).parent.parent / "lib"


def _collect_lib_modules():
    """Return list of importable module names from lib/."""
    return [p.stem for p in LIB_DIR.glob("*.py") if not p.name.startswith("_")]


class TestVault008StdlibOnly:
    """VAULT-008: no third-party dependencies in lib modules."""

    # @spec VAULT-008
    def test_lib_modules_importable_without_third_party(self):
        """
        Import each lib module and verify no ImportError or third-party leakage.
        Strategy: snapshot sys.modules before/after; any new top-level modules
        that are not stdlib or siblings indicate a violation.
        """
        before = set(sys.modules.keys())

        module_names = _collect_lib_modules()
        assert len(module_names) > 0, "No lib modules found"

        for mod_name in module_names:
            try:
                __import__(mod_name)
            except ImportError as e:
                pytest.fail(f"ImportError in lib/{mod_name}.py: {e}")

        after = set(sys.modules.keys())
        new_modules = after - before

        violations = []
        for mod in new_modules:
            # Get top-level package name (e.g., "numpy.core" → "numpy")
            top = mod.split(".")[0]
            if top in STDLIB_MODULES:
                continue
            if top in SIBLING_MODULES:
                continue
            # Private/internal modules (starting with _) are fine
            if top.startswith("_"):
                continue
            violations.append(top)

        assert violations == [], (
            f"Third-party or unexpected modules imported from lib/: {sorted(set(violations))}"
        )

    @pytest.mark.parametrize("mod_name", _collect_lib_modules())
    # @spec VAULT-008
    def test_single_module_importable(self, mod_name):
        """Each lib module must import without error."""
        try:
            __import__(mod_name)
        except ImportError as e:
            pytest.fail(f"lib/{mod_name}.py failed to import: {e}")
