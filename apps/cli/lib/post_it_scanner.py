#!/usr/bin/env python3
"""
post_it_scanner.py — Scan 05-Post-its/ and return ordered Post-it lists.

Active list:  pinned items first, then unpinned — within each group newest
              `created` first (R-2.1).
Archived list: newest `created` first.

Files with missing or unparseable frontmatter degrade gracefully: a warning is
logged and the file is skipped; no exception is raised.

Usage:
    python3 post_it_scanner.py --vault ~/vault-squirrel
    python3 post_it_scanner.py --vault ~/vault-squirrel --pretty
"""

import argparse
import datetime
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from intent_parser import parse_frontmatter  # noqa: E402

_log = logging.getLogger("post_it_scanner")

POST_ITS_DIR = Path("05-Post-its")

# Sentinel used as a sort key for items that have no parseable `created` value.
# Placed at the "oldest" end so items without a timestamp sort last.
_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _as_aware(dt: datetime.datetime) -> datetime.datetime:
    """Attach the local timezone to a naive datetime; leave aware ones alone."""
    if dt.tzinfo is None:
        return dt.astimezone()
    return dt


def _parse_dt(value) -> datetime.datetime | None:
    """Parse an ISO-8601 timestamp (date or datetime) to an aware datetime.

    Tolerates native date/datetime objects returned by the frontmatter parser.
    Returns None on failure.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return _as_aware(value)
    if isinstance(value, datetime.date):
        return _as_aware(datetime.datetime(value.year, value.month, value.day))
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("Z", "")
    try:
        return _as_aware(datetime.datetime.fromisoformat(s))
    except ValueError:
        try:
            return _as_aware(
                datetime.datetime.strptime(s.split("T")[0].split(" ")[0], "%Y-%m-%d")
            )
        except ValueError:
            return None


def _sort_key(item: dict) -> datetime.datetime:
    """Return an aware datetime for sorting; items without a valid `created`
    sort to the very end (treated as oldest)."""
    dt = _parse_dt(item.get("created"))
    return dt if dt is not None else _as_aware(_EPOCH)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def scan_post_its(vault_path: Path) -> dict:
    """Scan 05-Post-its/ for post_it files.

    Returns:
      {
        "active":   [...],   # pinned first, then newest-first by created
        "archived": [...],   # newest-first by created
        "scanned_at": ISO timestamp,
      }
    Each item: {id, text, color, label, pinned, state, created, converted_to, path}
    """
    now = datetime.datetime.now().astimezone()

    active: list[dict] = []
    archived: list[dict] = []

    folder = Path(vault_path).expanduser().resolve() / POST_ITS_DIR
    if not folder.exists():
        return {
            "active": [],
            "archived": [],
            "scanned_at": now.isoformat(),
        }

    for md_file in sorted(folder.rglob("*.md")):
        if md_file.name.startswith("."):
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(content)
        except Exception as exc:
            _log.warning("skipping unparseable file %s: %s", md_file, exc)
            continue

        # Only process post_it type files; silently skip others.
        if str(fm.get("type", "")).strip().lower() != "post_it":
            continue

        # Resolve fields with safe defaults.
        pi_id = str(fm.get("id", md_file.stem)).strip()
        state = str(fm.get("state", "active")).strip().lower()
        color = str(fm.get("color", "yellow")).strip()
        label = str(fm.get("label", "")).strip()
        created = str(fm.get("created", "")).strip()
        converted_to = str(fm.get("converted_to", "")).strip()

        # Parse `pinned` — defaults to False if missing or unparseable.
        raw_pinned = fm.get("pinned", False)
        if isinstance(raw_pinned, bool):
            pinned = raw_pinned
        else:
            pinned = str(raw_pinned).strip().lower() in ("true", "yes", "1")

        text = body.strip()

        entry = {
            "id": pi_id,
            "text": text,
            "color": color,
            "label": label,
            "pinned": pinned,
            "state": state,
            "created": created,
            "converted_to": converted_to,
            "path": str(md_file),
        }

        if state == "archived":
            archived.append(entry)
        else:
            # Treat any non-archived state (active or unknown) as active.
            active.append(entry)

    # R-2.1 ordering for active: pinned first, then newest-first within each group.
    pinned_items = sorted(
        [e for e in active if e["pinned"]],
        key=_sort_key,
        reverse=True,
    )
    unpinned_items = sorted(
        [e for e in active if not e["pinned"]],
        key=_sort_key,
        reverse=True,
    )
    active_sorted = pinned_items + unpinned_items

    # Archived: newest-first.
    archived_sorted = sorted(archived, key=_sort_key, reverse=True)

    return {
        "active": active_sorted,
        "archived": archived_sorted,
        "scanned_at": now.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(prog="post_it_scanner")
    p.add_argument("--vault", required=True)
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"Vault not found: {vault}", file=sys.stderr)
        sys.exit(1)

    result = scan_post_its(vault)
    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
