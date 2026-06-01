#!/usr/bin/env python3
"""
session_scanner.py — Finds recoverable sessions for /cb-recover.

Primary source:  vault/.squirrel/session-manifest.jsonl
Fallback source: ~/.claude/projects/*/*.jsonl  (Claude Code session history)

Filters sessions by:
- Age: within --max-age-hours (default 72)
- Environment: cwd must match allowed_inbound_environments from config

CLI:
    python3 session_scanner.py --vault ~/vault-tdah
    python3 session_scanner.py --vault ~/vault-tdah --max-age-hours 48 --pretty
"""

import argparse
import datetime
import json
import pathlib
import sys
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    cfg_path = pathlib.Path("~/.squirrel/config.toml").expanduser()
    if not cfg_path.exists():
        return {}
    config: dict = {}
    in_compliance = False
    for line in cfg_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s == "[compliance]":
            in_compliance = True
            continue
        if s.startswith("[") and s != "[compliance]":
            in_compliance = False
            continue
        if "=" in s:
            key, _, val = s.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if in_compliance:
                config.setdefault("compliance", {})[key] = val
            else:
                config[key] = val
    return config


# ─────────────────────────────────────────────────────────────────────────────
# Manifest reader (primary)
# ─────────────────────────────────────────────────────────────────────────────

def _read_manifest(vault: pathlib.Path, cutoff: datetime.datetime) -> list[dict]:
    manifest = vault / ".squirrel" / "session-manifest.jsonl"
    if not manifest.exists():
        return []

    entries = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_str = entry.get("timestamp", "")
        try:
            ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            ts = ts.replace(tzinfo=None)  # normalise to naive UTC
        except (ValueError, AttributeError):
            continue
        if ts >= cutoff:
            entries.append(entry)
    return entries


def _group_manifest_entries(entries: list[dict]) -> list[dict]:
    """Group manifest entries into sessions keyed by (session_id or cwd)."""
    groups: dict[str, dict] = {}
    for entry in entries:
        key = entry.get("session") or entry.get("cwd", "unknown")
        if key not in groups:
            groups[key] = {
                "source": "manifest",
                "session_id": entry.get("session", ""),
                "cwd": entry.get("cwd", ""),
                "files_edited": [],
                "first_seen": entry["timestamp"],
                "last_seen": entry["timestamp"],
                "entry_count": 0,
            }
        g = groups[key]
        fp = entry.get("file", "")
        if fp and fp not in g["files_edited"]:
            g["files_edited"].append(fp)
        if entry["timestamp"] > g["last_seen"]:
            g["last_seen"] = entry["timestamp"]
        if entry["timestamp"] < g["first_seen"]:
            g["first_seen"] = entry["timestamp"]
        g["entry_count"] += 1
    return list(groups.values())


# ─────────────────────────────────────────────────────────────────────────────
# Claude JSONL fallback
# ─────────────────────────────────────────────────────────────────────────────

def _parse_copilot_jsonl_row(line: str) -> "dict | None":
    """Extract file-path and project-hint from a Copilot session-state JSONL row.

    Returns None if the row is empty, malformed, or has an unrecognised schema.
    Only the two fields /sq-recover needs are extracted; everything else is ignored.
    """
    line = line.strip()
    if not line:
        return None
    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(row, dict):
        return None
    # Copilot session-state rows may use different field names across versions.
    # Try the most likely candidates; skip the row if neither is found.
    file_path = (
        row.get("file")
        or row.get("filePath")
        or row.get("file_path")
        or ""
    )
    project = (
        row.get("project")
        or row.get("project_tag")
        or row.get("projectTag")
        or row.get("workspace")
        or ""
    )
    if not file_path and not project:
        return None
    return {"file": file_path, "project": project}


def _read_copilot_jsonl_sessions(cutoff: datetime.datetime) -> list[dict]:
    """Scan $COPILOT_HOME/session-state/ for recently modified JSONL files."""
    import os
    session_state_dir = (
        pathlib.Path(os.environ.get("COPILOT_HOME", "~/.copilot")).expanduser()
        / "session-state"
    )
    if not session_state_dir.exists():
        return []

    sessions = []
    cutoff_ts = cutoff.timestamp()

    for jsonl in session_state_dir.glob("*.jsonl"):
        try:
            if jsonl.stat().st_mtime < cutoff_ts:
                continue
        except OSError:
            continue

        files_edited = []
        project = ""
        last_ts = None
        first_ts = None
        line_count = 0
        try:
            for line in jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
                parsed = _parse_copilot_jsonl_row(line)
                if parsed is None:
                    continue
                line_count += 1
                fp = parsed.get("file", "")
                if fp and fp not in files_edited:
                    files_edited.append(fp)
                proj = parsed.get("project", "")
                if proj and not project:
                    project = proj
                # Copilot rows may not carry a timestamp field; use file mtime.
        except OSError:
            continue

        if line_count == 0:
            continue

        try:
            mtime = jsonl.stat().st_mtime
        except OSError:
            mtime = 0.0

        ts_str = datetime.datetime.utcfromtimestamp(mtime).strftime("%Y-%m-%dT%H:%M:%SZ")

        sessions.append({
            "source": "copilot_jsonl",
            "session_id": jsonl.stem,
            "cwd": project,
            "jsonl_path": str(jsonl),
            "files_edited": files_edited,
            "first_seen": ts_str,
            "last_seen": ts_str,
            "entry_count": line_count,
        })

    return sessions


def _read_claude_jsonl_sessions(cutoff: datetime.datetime) -> list[dict]:
    """Scan ~/.claude/projects/ for recently modified JSONL session files."""
    projects_dir = pathlib.Path("~/.claude/projects").expanduser()
    if not projects_dir.exists():
        return []

    sessions = []
    cutoff_ts = cutoff.timestamp()

    for jsonl in projects_dir.rglob("*.jsonl"):
        try:
            if jsonl.stat().st_mtime < cutoff_ts:
                continue
        except OSError:
            continue

        # Infer cwd from the encoded directory name (Claude encodes path as folder)
        # ~/.claude/projects/-Users-javier-myproject/ → /Users/javier/myproject
        folder = jsonl.parent.name
        cwd = folder.replace("-", "/").lstrip("/")
        if not cwd.startswith("/"):
            cwd = "/" + cwd

        # Count Edit tool calls in the JSONL to build a file list
        files_edited = []
        last_ts = None
        first_ts = None
        line_count = 0
        try:
            for line in jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                line_count += 1
                ts_str = msg.get("timestamp", "")
                if ts_str:
                    if first_ts is None or ts_str < first_ts:
                        first_ts = ts_str
                    if last_ts is None or ts_str > last_ts:
                        last_ts = ts_str
                # Look for Edit tool inputs
                for tc in msg.get("content", []):
                    if isinstance(tc, dict) and tc.get("type") == "tool_use" and tc.get("name") == "Edit":
                        fp = tc.get("input", {}).get("file_path", "")
                        if fp and fp not in files_edited:
                            files_edited.append(fp)
        except OSError:
            continue

        if line_count == 0:
            continue

        sessions.append({
            "source": "claude_jsonl",
            "session_id": jsonl.stem,
            "cwd": cwd,
            "jsonl_path": str(jsonl),
            "files_edited": files_edited,
            "first_seen": first_ts or "",
            "last_seen": last_ts or "",
            "entry_count": line_count,
        })

    return sessions


# ─────────────────────────────────────────────────────────────────────────────
# Compliance filter
# ─────────────────────────────────────────────────────────────────────────────

# @spec SESSION-008
def _filter_by_environment(sessions: list[dict], config: dict) -> list[dict]:
    """
    When compliance.strict = true, exclude sessions whose cwd matches
    paths that look corporate (i.e., contain any domain from corporate_domains).
    For now: keep all sessions unless strict mode + corporate_domains is set.
    """
    compliance = config.get("compliance", {})
    if compliance.get("strict", "false").lower() != "true":
        return sessions

    raw_domains = compliance.get("corporate_domains", "[]")
    try:
        domains = json.loads(raw_domains)
    except (json.JSONDecodeError, ValueError):
        domains = []

    if not domains:
        return sessions

    filtered = []
    for s in sessions:
        cwd = s.get("cwd", "")
        if any(d in cwd for d in domains if d):
            continue  # skip corporate-cwd sessions
        filtered.append(s)
    return filtered


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

# @spec SESSION-007, SESSION-008
def scan_sessions(vault: pathlib.Path, max_age_hours: int, config: dict) -> list[dict]:
    cutoff = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(hours=max_age_hours)

    manifest_entries = _read_manifest(vault, cutoff)
    sessions = _group_manifest_entries(manifest_entries)

    if not sessions:
        claude_sessions = _read_claude_jsonl_sessions(cutoff)
        copilot_sessions = _read_copilot_jsonl_sessions(cutoff)
        sessions = claude_sessions + copilot_sessions

    sessions = _filter_by_environment(sessions, config)
    sessions.sort(key=lambda s: s.get("last_seen", ""), reverse=True)
    return sessions


def main() -> None:
    p = argparse.ArgumentParser(prog="session_scanner")
    p.add_argument("--vault", required=True, help="Path to vault root")
    p.add_argument("--max-age-hours", type=int, default=72)
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    vault = pathlib.Path(args.vault).expanduser().resolve()
    if not vault.exists():
        print(f"❌ Vault not found: {vault}", file=sys.stderr)
        sys.exit(1)

    config = _load_config()
    sessions = scan_sessions(vault, args.max_age_hours, config)

    indent = 2 if args.pretty else None
    print(json.dumps(sessions, indent=indent, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
