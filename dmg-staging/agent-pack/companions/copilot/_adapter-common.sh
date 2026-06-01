#!/usr/bin/env bash
# Shared helpers for Copilot hook adapters.
# Source this from hook-adapter.sh / hook-adapter-stdin.sh; do not execute directly.

# Resolve the active project tag from ~/.squirrel/state.json (or legacy per-vault state).
resolve_project() {
  python3 - <<'PY' 2>/dev/null || true
import json, pathlib, sys
state_path = pathlib.Path("~/.squirrel/state.json").expanduser()
if state_path.exists():
    try:
        d = json.loads(state_path.read_text())
        proj = d.get("last_active_project", "")
        if proj:
            print(proj)
            sys.exit(0)
    except Exception:
        pass
# Legacy: check per-vault state files
for legacy in pathlib.Path("~/.squirrel/state").expanduser().glob("*.json"):
    try:
        d = json.loads(legacy.read_text())
        proj = d.get("last_active_project", "")
        if proj:
            print(proj)
            sys.exit(0)
    except Exception:
        pass
print("")
PY
}

# Emit an ISO-8601 UTC timestamp.
iso_timestamp() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}
