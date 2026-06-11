#!/usr/bin/env python3
"""
fs_atomic — shared atomic-write helpers for vault and config files.

Single implementation of the temp-file + os.replace pattern previously
duplicated across the cli libs and server.py, with an fsync before the
replace so the new content is durable if the machine crashes right after
the write. stdlib only — no dependencias externas.
"""

import os
import tempfile
from pathlib import Path


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically (temp file in same dir + fsync + os.replace)."""
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write `text` to `path` atomically (temp file in same dir + fsync + os.replace)."""
    atomic_write_bytes(path, text.encode(encoding))
