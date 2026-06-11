"""
test_package_protocol.py — Tests for collect_files_by_scope scope validation.

Covers the H2 audit fix: scope strings are regex-validated before feeding
rglob patterns or path joins, and rglob results must resolve inside the vault.
"""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

from package_protocol import collect_files_by_scope


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    (v / "01-Active-Projects" / "PROJ").mkdir(parents=True)
    (v / "01-Active-Projects" / "PROJ" / "PROJ-001.md").write_text(
        "---\nid: PROJ-001\ntype: research\n---\n# Research note\n",
        encoding="utf-8",
    )
    (v / "TAG-001.md").write_text("# Tagged note\n", encoding="utf-8")
    return v


def test_valid_tag_scope_matches(vault: Path) -> None:
    files = collect_files_by_scope(vault, "TAG-001")
    assert [f["target_path"] for f in files] == ["TAG-001.md"]


def test_valid_project_scope_matches(vault: Path) -> None:
    files = collect_files_by_scope(vault, "PROJ:*")
    assert [f["target_path"] for f in files] == [
        "01-Active-Projects/PROJ/PROJ-001.md"
    ]


def test_traversal_tag_scope_returns_empty(vault: Path) -> None:
    assert collect_files_by_scope(vault, "../../etc/passwd") == []
    assert collect_files_by_scope(vault, "*") == []
    assert collect_files_by_scope(vault, "") == []


def test_traversal_project_scope_returns_empty(vault: Path) -> None:
    assert collect_files_by_scope(vault, "..:*") == []
    assert collect_files_by_scope(vault, "../..:research") == []


def test_unknown_kind_returns_empty(vault: Path) -> None:
    assert collect_files_by_scope(vault, "PROJ:passwords") == []


def test_symlink_escaping_vault_is_excluded(vault: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SECRET.md").write_text("# secret\n", encoding="utf-8")
    (vault / "linked").symlink_to(outside, target_is_directory=True)

    assert collect_files_by_scope(vault, "SECRET") == []
