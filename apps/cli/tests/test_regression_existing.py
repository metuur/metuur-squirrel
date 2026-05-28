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
        "f154b1dd57e303357c977a27b1e83ab1b9e376b8a41541eb9add966f0d11200d",
    "vault-minimal/01-Proyectos-Activos/TEST-PROJECT/TEST-PROJECT-AUTH-001.md":
        "5c146ae99fb7342d12d534c449e5d7f4b3a10c69ef9a42c741dba751ee47987c",
    "vault-minimal/01-Proyectos-Activos/TEST-PROJECT/TEST-PROJECT-AUTH-002.md":
        "c4c20ddc38c0daed0fe13ec46fca0bcc39fedae601c41bafa53282b7357b29e6",
    "vault-minimal/01-Proyectos-Activos/TEST-PROJECT/TEST-PROJECT.md":
        "b2813e002b79f6a1439d255fb3ddc212ae2638061ca13fd9eb06419adad0746f",
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
