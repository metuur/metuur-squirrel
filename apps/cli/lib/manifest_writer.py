#!/usr/bin/env python3
"""
manifest_writer.py — Called by the PostToolUse:Edit hook.

Appends one JSON line to vault/.squirrel/session-manifest.jsonl
using TOOL_INPUT, CWD, and CLAUDE_SESSION_ID env vars provided by Claude Code.
"""

import datetime
import json
import os
import pathlib
import sys

# @spec VAULT-008


def _read_vault_path() -> pathlib.Path | None:
    cfg = pathlib.Path("~/.squirrel/config.toml").expanduser()
    if not cfg.exists():
        return None
    for line in cfg.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("vault_path"):
            raw = s.split("=", 1)[1].strip().strip('"').strip("'")
            return pathlib.Path(raw).expanduser()
    return None


# @spec VAULT-006, SESSION-011
def main() -> None:
    vault = _read_vault_path()
    if not vault:
        return

    manifest_dir = vault / ".squirrel"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = manifest_dir / "session-manifest.jsonl"

    tool_input_raw = os.environ.get("TOOL_INPUT", "{}")
    try:
        tool_input = json.loads(tool_input_raw)
    except (json.JSONDecodeError, ValueError):
        tool_input = {}

    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "cwd": os.environ.get("CWD", os.getcwd()),
        "file": tool_input.get("file_path", ""),
        "event": "PostToolUse:Edit",
        "session": os.environ.get("CLAUDE_SESSION_ID", ""),
    }

    with open(manifest, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
