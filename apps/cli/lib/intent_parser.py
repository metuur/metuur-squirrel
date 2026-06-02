#!/usr/bin/env python3
"""
intent_parser.py — Parser de archivos intent del vault.

Parsea frontmatter YAML (simple, sin dependencias) + secciones Markdown,
y extrae estadísticas computadas (checkboxes done/total, días desde última actividad, etc.).

Uso programático:
    from intent_parser import parse_intent
    data = parse_intent(Path("archivo.md"))

Uso CLI:
    python3 intent_parser.py /path/to/intent.md
    python3 intent_parser.py /path/to/intent.md --field stats
"""

import argparse
import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

# @spec VAULT-008

# ─────────────────────────────────────────────────────────────────────────────
# Frontmatter parser — minimal YAML subset, no external deps
# ─────────────────────────────────────────────────────────────────────────────

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parse YAML frontmatter and return (frontmatter_dict, body_content).
    Supports:
      - scalar values: id: TAG-001
      - lists inline: tags: [intent, project/X]
      - lists block: see below
      - quoted strings
      - dates as strings (no conversion)
    """
    if not content.startswith("---"):
        return {}, content

    lines = content.splitlines(keepends=True)
    if len(lines) < 2:
        return {}, content

    # Find closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, content

    fm_text = "".join(lines[1:end_idx])
    body = "".join(lines[end_idx + 1:])

    fm = _parse_yaml_subset(fm_text)
    return fm, body


def _parse_yaml_subset(text: str) -> dict:
    """Parse a YAML subset. Handles: scalars, inline lists, block lists."""
    result = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if ":" not in line:
            i += 1
            continue

        # Key-value
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()

        # Skip indented lines (only top-level keys for now)
        if line.startswith(" ") or line.startswith("\t"):
            i += 1
            continue

        # Inline list: tags: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            items_str = val[1:-1].strip()
            if items_str:
                items = [x.strip().strip('"').strip("'") for x in items_str.split(",")]
                result[key] = [x for x in items if x]
            else:
                result[key] = []
            i += 1
            continue

        # Block list: tags:\n  - a\n  - b
        if not val and i + 1 < len(lines) and lines[i + 1].lstrip().startswith("- "):
            items = []
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("- "):
                item = lines[i].lstrip()[2:].strip().strip('"').strip("'")
                items.append(item)
                i += 1
            result[key] = items
            continue

        # Scalar
        val = val.strip('"').strip("'")
        result[key] = val
        i += 1

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Frontmatter writer — surgical, byte-preserving mutations
# ─────────────────────────────────────────────────────────────────────────────

# @spec R-1.6, R-1.7

# Sentinel used by write_frontmatter to mark a key for deletion.
_DELETE = object()

# Match a top-level frontmatter key line (no leading whitespace, has a colon).
_FM_KEY_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:(.*)$")


def write_frontmatter(path: Path, mutations: dict) -> None:
    """
    Apply mutations to the YAML frontmatter of a Markdown file in-place.

    - mutations[k] == _DELETE -> remove key k from the frontmatter entirely
      (drops the key line and any continuation lines belonging to it).
    - mutations[k] == <value>  -> upsert key k. Existing keys keep their
      position; new keys are appended at the end of the frontmatter block.
    - Keys NOT in mutations are left byte-identical (order, whitespace,
      comments and quoting preserved).
    - Body (everything after the closing `---`) is byte-identical.
    - If `mutations` is empty, the file is left untouched (no write).
    - If the file has no frontmatter block, the call is a no-op. This is
      out of scope for the intent files this helper targets.
    - File is written atomically: temp file in the same dir, then os.replace.
    - Encoding: utf-8.
    """
    if not mutations:
        return

    content = path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    # Locate frontmatter block: first line must be `---` (with its line ending);
    # find next `---` at start-of-line.
    if not lines or lines[0].rstrip("\r\n") != "---":
        # No frontmatter — out of scope, no-op.
        return

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            end_idx = i
            break
    if end_idx is None:
        return  # malformed frontmatter, no-op

    fm_lines = lines[1:end_idx]           # between the two `---` markers
    header_line = lines[0]                # opening `---\n`
    closing_line = lines[end_idx]         # closing `---\n`
    body_lines = lines[end_idx + 1:]      # body, byte-identical

    # Detect dominant newline style for any appended lines.
    newline = _detect_newline(header_line, fm_lines, closing_line)

    seen_keys: set = set()
    new_fm_lines: list = []
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        stripped_line = line.lstrip()
        # Skip top-level key detection for indented / blank / comment lines:
        # they always travel with the preceding key (or stand alone).
        if (
            line.startswith(" ")
            or line.startswith("\t")
            or not stripped_line.strip()
            or stripped_line.startswith("#")
        ):
            new_fm_lines.append(line)
            i += 1
            continue

        m = _FM_KEY_PATTERN.match(line.rstrip("\r\n"))
        if not m:
            new_fm_lines.append(line)
            i += 1
            continue

        key = m.group(1)
        if key not in mutations:
            new_fm_lines.append(line)
            i += 1
            continue

        # This key is being mutated.
        seen_keys.add(key)
        # Collect continuation lines (indented or block-list `- ...`) so we
        # can drop them together with the key on delete.
        cont_start = i + 1
        cont_end = cont_start
        while cont_end < len(fm_lines):
            nxt = fm_lines[cont_end]
            nxt_stripped = nxt.lstrip()
            if nxt.startswith(" ") or nxt.startswith("\t"):
                cont_end += 1
                continue
            if nxt_stripped.startswith("- "):
                cont_end += 1
                continue
            break

        value = mutations[key]
        if value is _DELETE:
            # Drop the key line and all its continuation lines.
            i = cont_end
            continue

        # Upsert: replace the key line, drop its continuation lines (the new
        # scalar value owns the whole entry). For the targeted use-case
        # (focus_today: ISO-date, focus_week: GGGG-Www) a plain scalar is safe.
        new_fm_lines.append(f"{key}: {value}{newline}")
        i = cont_end

    # Append keys that weren't found and are not _DELETE.
    for key, value in mutations.items():
        if key in seen_keys or value is _DELETE:
            continue
        new_fm_lines.append(f"{key}: {value}{newline}")

    new_content = "".join([header_line, *new_fm_lines, closing_line, *body_lines])

    new_bytes = new_content.encode("utf-8")
    if new_bytes == content.encode("utf-8"):
        return  # no effective change, skip the write

    _atomic_write_bytes(path, new_bytes)


def _detect_newline(header_line: str, fm_lines: list, closing_line: str) -> str:
    """Return the dominant line ending used in the frontmatter block."""
    for ln in (header_line, *fm_lines, closing_line):
        if ln.endswith("\r\n"):
            return "\r\n"
        if ln.endswith("\n"):
            return "\n"
    return "\n"


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write `data` to `path` atomically (temp file in same dir + os.replace)."""
    directory = path.parent
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(directory)
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Section parser — split body into named sections by H2 headings
# ─────────────────────────────────────────────────────────────────────────────

# Map of common Spanish section names to canonical English keys
SECTION_NAME_MAP = {
    # Spanish → canonical
    "objetivo": "objective",
    "intent": "intent",
    "intent (qué/por qué)": "intent",
    "definition of done": "definition_of_done",
    "tareas concretas": "tasks",
    "tareas concretas (next physical actions)": "tasks",
    "tareas": "tasks",
    "notas": "notes",
    "notas / context": "notes",
    "notas / contexto": "notes",
    "relacionados": "related",
    "shutdown notes": "shutdown_notes",
    "shutdown notes (más reciente arriba)": "shutdown_notes",
    "open questions": "open_questions",
    "context dump": "context_dump",
    "componentes e intents": "components",
    "decisiones": "decisions",
    "stakeholders": "stakeholders",
    "comunicación": "communication",
    # English passthrough
    "objective": "objective",
    "tasks": "tasks",
    "notes": "notes",
    "related": "related",
    "components": "components",
}

# Match H2 with optional emoji prefix: "## 🎯 Objetivo" or "## Objetivo"
HEADING_PATTERN = re.compile(r"^##\s+(?:[\W\d_]*\s+)?(.+?)\s*$", re.MULTILINE)


def parse_sections(body: str) -> dict[str, str]:
    """Split markdown body into sections keyed by canonical section names."""
    matches = list(HEADING_PATTERN.finditer(body))
    sections = {}

    for idx, match in enumerate(matches):
        heading = match.group(1).strip().lower()
        canonical = SECTION_NAME_MAP.get(heading, heading.replace(" ", "_"))

        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        content = body[start:end].strip()

        sections[canonical] = content

    return sections


# ─────────────────────────────────────────────────────────────────────────────
# Checkbox parser — extract Definition of Done done/total
# ─────────────────────────────────────────────────────────────────────────────

CHECKBOX_PATTERN = re.compile(r"^-\s+\[([ xX])\]\s+(.+?)$", re.MULTILINE)


def parse_checkboxes(text: str) -> tuple[list[str], list[str]]:
    """Return (done_items, pending_items)."""
    done = []
    pending = []
    for match in CHECKBOX_PATTERN.finditer(text):
        marker = match.group(1).lower()
        item = match.group(2).strip()
        if marker == "x":
            done.append(item)
        else:
            pending.append(item)
    return done, pending


# ─────────────────────────────────────────────────────────────────────────────
# Shutdown notes parser — extract structured shutdown entries
# ─────────────────────────────────────────────────────────────────────────────

# Match: "### 2026-05-22 17:30" or "### 2026-05-22"
SHUTDOWN_HEADING_PATTERN = re.compile(
    r"^###\s+(\d{4}-\d{2}-\d{2}(?:\s+\d{1,2}:\d{2})?)",
    re.MULTILINE,
)

# Match bullet fields: "- **Estado**: ..." or "- Estado: ..."
BULLET_FIELD_PATTERN = re.compile(
    r"^-\s+\*?\*?(\w[\w\s/]*?)\*?\*?\s*:\s*(.+?)(?=\n-\s|\n###|\n##|\n*$)",
    re.MULTILINE | re.DOTALL,
)


def parse_shutdown_notes(text: str) -> list[dict]:
    """Parse the shutdown_notes section into structured entries."""
    if not text:
        return []

    entries = []
    headings = list(SHUTDOWN_HEADING_PATTERN.finditer(text))

    for idx, h in enumerate(headings):
        timestamp = h.group(1).strip()
        start = h.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
        chunk = text[start:end]

        entry = {"timestamp": timestamp, "raw": chunk.strip()}

        # Extract bullet fields
        for fm in BULLET_FIELD_PATTERN.finditer(chunk):
            field_name = fm.group(1).strip().lower().replace(" ", "_")
            value = fm.group(2).strip()
            # Map shutdown-note bullet labels to canonical keys
            field_map = {
                "next_physical_action": "next_action",
                "next": "next_action",
                "active_hypothesis": "hypothesis",
                "hypothesis": "hypothesis",
                "blocked_by": "blocked_by",
                "decisions_made_today": "decisions",
                "decisions": "decisions",
                "open_loops": "open_loops",
                "hemingway": "hemingway",
            }
            entry[field_map.get(field_name, field_name)] = value

        entries.append(entry)

    # Most recent first (assume notes appended at top)
    return entries


# ─────────────────────────────────────────────────────────────────────────────
# Stats computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_stats(frontmatter: dict, sections: dict, body: str) -> dict:
    """Compute derived stats from parsed intent."""
    # Definition of Done progress
    dod_text = sections.get("definition_of_done", "")
    dod_done, dod_pending = parse_checkboxes(dod_text)

    # Task list progress
    tasks_text = sections.get("tasks", "")
    tasks_done, tasks_pending = parse_checkboxes(tasks_text)

    # Shutdown notes
    shutdown_notes = parse_shutdown_notes(sections.get("shutdown_notes", ""))
    last_activity = None
    days_since_activity = None

    if shutdown_notes:
        ts_str = shutdown_notes[0]["timestamp"]
        last_activity = _parse_timestamp(ts_str)
        if last_activity:
            now = datetime.datetime.now()
            delta = now - last_activity
            days_since_activity = delta.days

    # Deadline calculation
    deadline_str = frontmatter.get("deadline")
    days_to_deadline = None
    deadline_passed = False
    if deadline_str:
        deadline = _parse_date(deadline_str)
        if deadline:
            today = datetime.date.today()
            delta = (deadline - today).days
            days_to_deadline = delta
            deadline_passed = delta < 0

    total_dod = len(dod_done) + len(dod_pending)
    percent_done = int(100 * len(dod_done) / total_dod) if total_dod > 0 else 0

    return {
        "definition_of_done": {
            "done": dod_done,
            "pending": dod_pending,
            "total": total_dod,
            "done_count": len(dod_done),
            "percent_done": percent_done,
        },
        "tasks": {
            "done": tasks_done,
            "pending": tasks_pending,
            "total": len(tasks_done) + len(tasks_pending),
            "done_count": len(tasks_done),
        },
        "shutdown_notes_count": len(shutdown_notes),
        "last_activity": last_activity.isoformat() if last_activity else None,
        "days_since_activity": days_since_activity,
        "deadline": deadline_str,
        "days_to_deadline": days_to_deadline,
        "deadline_passed": deadline_passed,
        "status": frontmatter.get("status", "unknown"),
    }


def _parse_date(s: str) -> Optional[datetime.date]:
    """Parse a date string like '2026-05-23' or '2026-05-23T10:00'."""
    if not s:
        return None
    s = s.strip()
    # Try multiple formats
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.datetime.strptime(s.split("T")[0].split(" ")[0], "%Y-%m-%d").date()
        except (ValueError, IndexError):
            continue
    return None


def _parse_timestamp(s: str) -> Optional[datetime.datetime]:
    """Parse '2026-05-22 17:30' or '2026-05-22T17:30' or just '2026-05-22'."""
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Title extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_title(body: str) -> str:
    """Extract first H1 title."""
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Main parse function
# ─────────────────────────────────────────────────────────────────────────────

# @spec VAULT-005
def parse_intent(path: Path) -> dict:
    """
    Parse an intent file fully.
    Returns a dict with: id, path, title, frontmatter, sections, stats, shutdown_notes.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    content = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    sections = parse_sections(body)
    title = extract_title(body)
    stats = compute_stats(frontmatter, sections, body)
    shutdown_notes = parse_shutdown_notes(sections.get("shutdown_notes", ""))

    intent_id = frontmatter.get("id") or path.stem

    return {
        "id": intent_id,
        "path": str(path),
        "title": title,
        "frontmatter": frontmatter,
        "sections": sections,
        "shutdown_notes": shutdown_notes,
        "stats": stats,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(prog="intent_parser")
    p.add_argument("path", help="Path to intent .md file")
    p.add_argument("--field", help="Print only a specific top-level field", default=None)
    p.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = p.parse_args()

    try:
        data = parse_intent(Path(args.path))
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    if args.field:
        if args.field not in data:
            print(f"❌ Field not found: {args.field}", file=sys.stderr)
            print(f"   Available: {', '.join(data.keys())}", file=sys.stderr)
            sys.exit(1)
        output = data[args.field]
    else:
        output = data

    indent = 2 if args.pretty else None
    print(json.dumps(output, indent=indent, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
