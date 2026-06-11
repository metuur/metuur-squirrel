#!/usr/bin/env python3
"""
post_it_writer.py — Create and mutate Post-it files in 05-Post-its/.

Post-its are lightweight sticky notes stored as markdown files named PI-NNN.md.
Each has a minimal frontmatter with no task-oriented fields (no status,
reminder_date, or due).

Public API:
    create(vault_path, text, color, label) -> str   # returns "PI-001"
    update(vault_path, pi_id, fields)               # fields: text/color/label/pinned
    archive(vault_path, pi_id)
    restore(vault_path, pi_id)
    delete(vault_path, pi_id)
    record_conversion(vault_path, pi_id, ref)
    resolve_post_it_path(vault_path, pi_id) -> Path | None
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from intent_parser import write_frontmatter, parse_intent  # noqa: E402
from fs_atomic import atomic_write_text  # noqa: E402

POST_ITS_DIR = Path("05-Post-its")
_ID_PREFIX = "PI"


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _post_its_dir(vault_path: Path) -> Path:
    return Path(vault_path).expanduser().resolve() / POST_ITS_DIR


def _next_number(folder: Path, prefix: str) -> int:
    """Smallest N such that `<prefix>-<NNN>.md` is unused in `folder`.

    Scans ALL .md files so IDs are never reused.
    """
    used: set[int] = set()
    pat = re.compile(re.escape(prefix) + r"-(\d{3})\.md$", re.IGNORECASE)
    if folder.exists():
        for entry in folder.glob(f"{prefix}-*.md"):
            m = pat.search(entry.name)
            if m:
                used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return n


def _format_post_it(
    *,
    pi_id: str,
    text: str,
    color: str,
    label: str,
    created_iso: str,
) -> str:
    return (
        "---\n"
        f"id: {pi_id}\n"
        "type: post_it\n"
        "state: active\n"
        f"color: {color}\n"
        f"label: {label}\n"
        "pinned: false\n"
        f"created: {created_iso}\n"
        "converted_to: \"\"\n"
        "---\n\n"
        f"{text}\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def create(
    vault_path: Path,
    text: str,
    color: str = "yellow",
    label: str = "",
) -> str:
    """Create a new Post-it. Returns the new id (e.g. "PI-001").

    Writes PI-NNN.md under 05-Post-its/ atomically, creating the folder if
    absent. Never writes status, reminder_date, or due.
    """
    vault_path = Path(vault_path).expanduser().resolve()
    folder = _post_its_dir(vault_path)
    folder.mkdir(parents=True, exist_ok=True)

    nnn = _next_number(folder, _ID_PREFIX)
    pi_id = f"{_ID_PREFIX}-{nnn:03d}"
    target = folder / f"{pi_id}.md"

    now = datetime.datetime.now().astimezone()
    body = _format_post_it(
        pi_id=pi_id,
        text=text,
        color=color,
        label=label,
        created_iso=now.isoformat(),
    )

    atomic_write_text(target, body)
    return pi_id


def resolve_post_it_path(vault_path: Path, pi_id: str) -> Path | None:
    """Resolve a Post-it id to its file under 05-Post-its/, or None.

    Only ever resolves inside 05-Post-its/, never elsewhere in the vault.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", pi_id or ""):
        return None
    candidate = _post_its_dir(vault_path) / f"{pi_id}.md"
    return candidate if candidate.exists() else None


def update(vault_path: Path, pi_id: str, fields: dict) -> None:
    """Update a subset of {text, color, label, pinned} on a Post-it.

    Frontmatter fields (color, label, pinned) are updated via write_frontmatter.
    Text body changes rewrite the full file atomically.
    """
    path = resolve_post_it_path(vault_path, pi_id)
    if path is None:
        raise FileNotFoundError(f"Post-it not found: {pi_id}")

    fm_mutations: dict = {}
    if "color" in fields:
        fm_mutations["color"] = fields["color"]
    if "label" in fields:
        fm_mutations["label"] = fields["label"]
    if "pinned" in fields:
        fm_mutations["pinned"] = str(fields["pinned"]).lower()

    if fm_mutations:
        write_frontmatter(path, fm_mutations)

    if "text" in fields:
        # Re-read the updated frontmatter block, replace the body.
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)
        # Find the closing --- of the frontmatter.
        end_idx = None
        if lines and lines[0].rstrip("\r\n") == "---":
            for i in range(1, len(lines)):
                if lines[i].rstrip("\r\n") == "---":
                    end_idx = i
                    break
        if end_idx is not None:
            fm_block = "".join(lines[: end_idx + 1])
            new_content = fm_block + "\n" + fields["text"] + "\n"
        else:
            # No frontmatter — just replace everything.
            new_content = fields["text"] + "\n"
        atomic_write_text(path, new_content)


def archive(vault_path: Path, pi_id: str) -> None:
    """Set state: archived on a Post-it."""
    path = resolve_post_it_path(vault_path, pi_id)
    if path is None:
        raise FileNotFoundError(f"Post-it not found: {pi_id}")
    write_frontmatter(path, {"state": "archived"})


def restore(vault_path: Path, pi_id: str) -> None:
    """Set state: active on a Post-it."""
    path = resolve_post_it_path(vault_path, pi_id)
    if path is None:
        raise FileNotFoundError(f"Post-it not found: {pi_id}")
    write_frontmatter(path, {"state": "active"})


def delete(vault_path: Path, pi_id: str) -> None:
    """Remove a Post-it file."""
    path = resolve_post_it_path(vault_path, pi_id)
    if path is None:
        raise FileNotFoundError(f"Post-it not found: {pi_id}")
    path.unlink(missing_ok=True)


def record_conversion(vault_path: Path, pi_id: str, ref: str) -> None:
    """Mark a Post-it as converted: state=archived, converted_to=ref."""
    path = resolve_post_it_path(vault_path, pi_id)
    if path is None:
        raise FileNotFoundError(f"Post-it not found: {pi_id}")
    write_frontmatter(path, {"state": "archived", "converted_to": ref})
