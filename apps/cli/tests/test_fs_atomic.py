"""
test_fs_atomic.py — Tests for the shared atomic-write helper (M5 audit fix).
"""

import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent / "lib"
sys.path.insert(0, str(LIB_DIR))

from fs_atomic import atomic_write_bytes, atomic_write_text


def test_writes_new_file(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    atomic_write_text(target, "# hello\n")
    assert target.read_text(encoding="utf-8") == "# hello\n"


def test_replaces_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    target.write_text("old", encoding="utf-8")
    atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_no_temp_file_left_behind(tmp_path: Path) -> None:
    target = tmp_path / "note.md"
    atomic_write_text(target, "content")
    assert [p.name for p in tmp_path.iterdir()] == ["note.md"]


def test_bytes_roundtrip(tmp_path: Path) -> None:
    target = tmp_path / "data.bin"
    atomic_write_bytes(target, b"\x00\x01\x02")
    assert target.read_bytes() == b"\x00\x01\x02"


def test_missing_directory_raises_and_leaves_no_tmp(tmp_path: Path) -> None:
    target = tmp_path / "missing" / "note.md"
    with pytest.raises(FileNotFoundError):
        atomic_write_text(target, "content")
    assert not (tmp_path / "missing").exists()
