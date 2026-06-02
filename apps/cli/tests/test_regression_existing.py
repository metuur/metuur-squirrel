#!/usr/bin/env python3
"""
Story 5.1 — assert the existing test suite + fixtures survive multi-vault changes.

Acceptance (from docs/ears/multi-vault-core.md):
  R-9.2: THE SYSTEM SHALL keep all existing tests in tests/ passing without
         modification.

Verify (from docs/tasks/multi-vault-core.md story 5.1):
  python3 -m unittest discover tests from repo root exits 0; the test count
  is at least the pre-change count. Every fixture in tests/fixtures/ is
  untouched.

How this guards:
  - PRE_CHANGE_TEST_COUNT is the unittest count from the multi-vault-core
    baseline (pre-Unit-1). The current suite must keep at least that many
    tests; the baseline is the regression floor, not a ceiling.
  - FIXTURE_HASHES pins the SHA-256 of every file under tests/fixtures/.
    If anyone edits a fixture, this test fails. Intentional fixture edits
    must update the hash AND the commit must explain why R-9.2 still holds.
"""

import hashlib
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"

# Baseline test count is a regression FLOOR, not a ceiling. New work may
# only add tests; removing or skipping an existing test trips this guard.
# Re-baselined after web-ui-simple shipped (was 204 → 218 → 239 → 334).
PRE_CHANGE_TEST_COUNT = 204

# Pinned SHA-256 of every fixture file. Run this to refresh after an
# intentional fixture edit (and explain why in the commit message):
#   find tests/fixtures -type f | sort | xargs shasum -a 256
FIXTURE_HASHES = {
    "vault-minimal/01-Proyectos-Activos/SIDEPROJECT-STALE/SIDEPROJECT-STALE.md":
        "a212962324cac2826d431c9ea10adebf7d274e8e64fb55f9919abff5f8763a99",
    "vault-minimal/01-Proyectos-Activos/TEST-PROJECT/TEST-PROJECT-AUTH-001.md":
        "cd35ec09444b0e97c9101beca85deec6e08ecb3487242ec1e56860445968a0a3",
    "vault-minimal/01-Proyectos-Activos/TEST-PROJECT/TEST-PROJECT-AUTH-002.md":
        "9b80d10f5e67e0398f9152a786ee29ccc1a83fe4c0f034947ad12b5a5547c157",
    "vault-minimal/01-Proyectos-Activos/TEST-PROJECT/TEST-PROJECT.md":
        "2c755e7d21df55a8b01ef39d3e888564261aef2292c06db89cb7ca8c9f8a64cc",
}


class TestExistingTestsStillCovered(unittest.TestCase):
    """R-9.2 — test count must not regress below the pre-change baseline."""

    def test_total_test_count_at_or_above_baseline(self):
        loader = unittest.TestLoader()
        suite = loader.discover(start_dir=str(REPO / "tests"))
        count = suite.countTestCases()
        self.assertGreaterEqual(
            count,
            PRE_CHANGE_TEST_COUNT,
            msg=(
                f"test count regression: only {count} tests discovered, "
                f"baseline is {PRE_CHANGE_TEST_COUNT}. Multi-vault changes "
                f"may only ADD tests; removing or skipping existing tests "
                f"violates R-9.2."
            ),
        )


class TestFixturesUntouched(unittest.TestCase):
    """R-9.2 — every fixture in tests/fixtures/ is byte-identical to baseline."""

    def test_fixture_set_matches_baseline_exactly(self):
        # New, unexpected fixtures must explain themselves: add them to
        # FIXTURE_HASHES with the rationale in the commit message.
        present = {
            str(p.relative_to(FIXTURES)).replace("\\", "/")
            for p in FIXTURES.rglob("*")
            if p.is_file()
        }
        expected = set(FIXTURE_HASHES.keys())
        self.assertEqual(
            present,
            expected,
            msg=(
                f"fixture set drifted: extra={present - expected}, "
                f"missing={expected - present}. Pin new fixtures in "
                f"FIXTURE_HASHES (story 5.1) and justify in the commit."
            ),
        )

    def test_each_fixture_byte_identical_to_baseline(self):
        for rel_path, expected_sha in FIXTURE_HASHES.items():
            with self.subTest(fixture=rel_path):
                p = FIXTURES / rel_path
                self.assertTrue(p.is_file(), f"missing fixture: {p}")
                actual = hashlib.sha256(p.read_bytes()).hexdigest()
                self.assertEqual(
                    actual,
                    expected_sha,
                    msg=(
                        f"fixture mutated: {rel_path}\n"
                        f"  expected SHA-256: {expected_sha}\n"
                        f"  actual SHA-256:   {actual}\n"
                        f"R-9.2 requires fixtures to remain untouched."
                    ),
                )


if __name__ == "__main__":
    unittest.main()
