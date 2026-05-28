"""Tests for SYNC-001..008: package protocol generation, validation, and apply."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from package_protocol import (
    START_MARKER,
    END_MARKER,
    compute_payload_hash,
    collect_files_by_scope,
    generate_package,
    parse_package,
    validate_package,
    apply_package,
)


def _make_vault(tmp: Path) -> Path:
    vault = tmp / "vault"
    (vault / "01-Proyectos-Activos" / "PROJ-A").mkdir(parents=True)
    (vault / ".squirrel" / "applied").mkdir(parents=True)
    return vault


def _fe(path: str, content: str, tag: str = "TEST-001") -> dict:
    """Build a minimal file entry dict for generate_package."""
    return {
        "target_path": path,
        "content": content,
        "operation": "create",
        "tag": tag,
        "conflict_policy": "skip",
        "description": "(test)",
    }


def _simple_files():
    return [_fe("01-Test/note.md", "# Hello\ncontent here")]


class TestSync001PackageGeneration(unittest.TestCase):
    """SYNC-001: generate_package emits SQUIRREL-PACKAGE block with required header fields."""

    # @spec SYNC-001
    def test_start_marker_is_squirrel_package(self):
        self.assertIn("SQUIRREL-PACKAGE", START_MARKER)

    # @spec SYNC-001
    def test_end_marker_is_squirrel_package(self):
        self.assertIn("SQUIRREL-PACKAGE", END_MARKER)

    # @spec SYNC-001
    def test_generate_contains_start_and_end_markers(self):
        pkg = generate_package(_simple_files(), from_env="personal", to_env="work", scope="TAG-TEST")
        self.assertIn(START_MARKER, pkg)
        self.assertIn(END_MARKER, pkg)

    # @spec SYNC-001
    def test_generate_contains_required_header_fields(self):
        pkg = generate_package(
            _simple_files(), from_env="personal", to_env="work", scope="TAG-TEST", intent="test"
        )
        for field in ("from", "to", "generated_at", "scope", "hash_sha256", "intent"):
            self.assertIn(field, pkg, f"Missing header field: {field}")

    # @spec SYNC-001
    def test_generate_includes_sha256(self):
        files = _simple_files()
        expected_hash = compute_payload_hash(files)
        pkg = generate_package(files, from_env="personal", to_env="work", scope="TAG")
        self.assertIn(expected_hash, pkg)

    # @spec SYNC-001
    def test_generate_one_section_per_file(self):
        files = [
            _fe("01-Test/a.md", "# A"),
            _fe("01-Test/b.md", "# B"),
        ]
        pkg = generate_package(files, from_env="personal", to_env="work", scope="TAG")
        self.assertIn("Archivo 1:", pkg)
        self.assertIn("Archivo 2:", pkg)


class TestSync002ExplicitScope(unittest.TestCase):
    """SYNC-002: scope must be explicit; collect_files_by_scope requires a scope string."""

    # @spec SYNC-002
    def test_single_tag_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "01-Proyectos-Activos" / "PROJ-A").mkdir(parents=True)
            note = vault / "01-Proyectos-Activos" / "PROJ-A" / "TAG-001.md"
            note.write_text("# TAG-001")
            files = collect_files_by_scope(vault, "TAG-001")
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]["tag"], "TAG-001")

    # @spec SYNC-002
    def test_project_wildcard_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            proj_dir = vault / "01-Proyectos-Activos" / "PROJ-A"
            proj_dir.mkdir(parents=True)
            (proj_dir / "note1.md").write_text("# Note 1")
            (proj_dir / "note2.md").write_text("# Note 2")
            files = collect_files_by_scope(vault, "PROJ-A:*")
            self.assertEqual(len(files), 2)

    # @spec SYNC-002
    def test_empty_scope_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            vault.mkdir(parents=True, exist_ok=True)
            files = collect_files_by_scope(vault, "NONEXISTENT-TAG")
            self.assertEqual(files, [])


class TestSync003HashVerification(unittest.TestCase):
    """SYNC-003: validate_package verifies SHA-256 before vault mutation."""

    def _make_valid_package(self):
        files = _simple_files()
        text = generate_package(files, from_env="personal", to_env="work", scope="TAG")
        return parse_package(text)

    # @spec SYNC-003
    def test_valid_package_passes(self):
        pkg = self._make_valid_package()
        ok, errors = validate_package(pkg)
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    # @spec SYNC-003
    def test_tampered_content_fails_hash_check(self):
        files = _simple_files()
        text = generate_package(files, from_env="personal", to_env="work", scope="TAG")
        # Tamper with content after generation
        pkg = parse_package(text)
        pkg["files"][0]["content"] = "# Tampered content"
        ok, errors = validate_package(pkg)
        self.assertFalse(ok)
        self.assertTrue(any("Hash mismatch" in e for e in errors))

    # @spec SYNC-003
    def test_missing_header_field_fails(self):
        pkg = self._make_valid_package()
        del pkg["header"]["hash_sha256"]
        ok, errors = validate_package(pkg)
        self.assertFalse(ok)
        self.assertTrue(any("hash_sha256" in e for e in errors))

    # @spec SYNC-003
    def test_unsafe_path_fails(self):
        pkg = self._make_valid_package()
        pkg["files"][0]["target_path"] = "../etc/passwd"
        # Recompute hash to pass hash check
        pkg["header"]["hash_sha256"] = compute_payload_hash(
            [{"target_path": f["target_path"], "content": f["content"]} for f in pkg["files"]]
        )
        ok, errors = validate_package(pkg)
        self.assertFalse(ok)
        self.assertTrue(any("Unsafe path" in e for e in errors))

    # @spec SYNC-003
    def test_missing_start_marker_raises(self):
        with self.assertRaises(ValueError):
            parse_package("no markers here")


class TestSync005AuditRecord(unittest.TestCase):
    """SYNC-005: apply writes audit record to .squirrel/applied/<timestamp>-<hash>.json."""

    # @spec SYNC-005
    def test_audit_record_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(Path(tmp))
            files = [_fe("01-Proyectos-Activos/PROJ-A/note.md", "# Test")]
            text = generate_package(files, from_env="personal", to_env="work", scope="PROJ-A:*")
            pkg = parse_package(text)
            result = apply_package(pkg, vault, dry_run=False, interactive=False)
            self.assertIn("audit_log", result)
            audit_path = Path(result["audit_log"])
            self.assertTrue(audit_path.exists())
            audit = json.loads(audit_path.read_text())
            self.assertIn("package_hash", audit)
            self.assertIn("scope", audit)
            self.assertIn("operations", audit)

    # @spec SYNC-005
    def test_dry_run_no_audit_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(Path(tmp))
            files = [_fe("01-Proyectos-Activos/PROJ-A/note.md", "# Test")]
            text = generate_package(files, from_env="personal", to_env="work", scope="PROJ-A:*")
            pkg = parse_package(text)
            result = apply_package(pkg, vault, dry_run=True, interactive=False)
            self.assertNotIn("audit_log", result)


class TestSync006Idempotency(unittest.TestCase):
    """SYNC-006: applying the same package twice is a no-op on second apply."""

    # @spec SYNC-006
    def test_second_apply_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(Path(tmp))
            files = [_fe("01-Proyectos-Activos/PROJ-A/idem.md", "# Idem")]
            text = generate_package(files, from_env="personal", to_env="work", scope="PROJ-A:*")
            pkg = parse_package(text)

            result1 = apply_package(pkg, vault, dry_run=False, interactive=False)
            self.assertNotIn("already_applied", result1)
            self.assertEqual(result1["created"], 1)

            result2 = apply_package(pkg, vault, dry_run=False, interactive=False)
            self.assertTrue(result2.get("already_applied"))
            self.assertEqual(result2["created"], 0)

    # @spec SYNC-006
    def test_different_package_is_not_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(Path(tmp))
            files_a = [_fe("01-Proyectos-Activos/PROJ-A/a.md", "# A")]
            files_b = [_fe("01-Proyectos-Activos/PROJ-A/b.md", "# B")]
            pkg_a = parse_package(generate_package(files_a, "personal", "work", "PROJ-A:*"))
            pkg_b = parse_package(generate_package(files_b, "personal", "work", "PROJ-A:*"))

            apply_package(pkg_a, vault, dry_run=False, interactive=False)
            result = apply_package(pkg_b, vault, dry_run=False, interactive=False)
            self.assertNotIn("already_applied", result)
            self.assertEqual(result["created"], 1)


class TestSync007NoNetwork(unittest.TestCase):
    """SYNC-007: no network calls in package generation or application."""

    # @spec SYNC-007
    def test_generate_does_not_import_network_modules(self):
        """Verify package_protocol.py doesn't import requests, urllib.request, http.client for transport."""
        import package_protocol
        import importlib
        import inspect
        source = inspect.getsource(package_protocol)
        for forbidden in ("requests.get", "requests.post", "urllib.request.urlopen", "socket.connect"):
            self.assertNotIn(forbidden, source, f"Found network call: {forbidden}")


class TestSync008AtomicPerNote(unittest.TestCase):
    """SYNC-008: when one note fails, others are unaffected."""

    # @spec SYNC-008
    def test_path_traversal_fails_single_note_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = _make_vault(Path(tmp))
            pkg = {
                "header": {
                    "from": "personal",
                    "to": "work",
                    "generated_at": "2026-01-01T00:00:00Z",
                    "scope": "TAG",
                    "files_count": "2",
                    "hash_sha256": "dummy",
                    "intent": "",
                },
                "files": [
                    {"target_path": "../evil.md", "operation": "create", "tag": "BAD", "conflict_policy": "skip", "content": "evil"},
                    {"target_path": "01-Proyectos-Activos/PROJ-A/ok.md", "operation": "create", "tag": "OK", "conflict_policy": "skip", "content": "# OK"},
                ],
            }
            result = apply_package(pkg, vault, dry_run=False, interactive=False)
            self.assertEqual(result["failed"], 1)
            # The good note was still applied
            ok_file = vault / "01-Proyectos-Activos" / "PROJ-A" / "ok.md"
            self.assertTrue(ok_file.exists())


if __name__ == "__main__":
    unittest.main()
