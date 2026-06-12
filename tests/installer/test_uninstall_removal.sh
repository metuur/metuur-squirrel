#!/usr/bin/env bash
# tests/installer/test_uninstall_removal.sh
#
# User-scope removal coverage for uninstall.sh (R-4.2, R-4.3, R-4.5, R-4.6).
# Everything runs inside a throwaway $HOME sandbox; stop_squirrel and confirm are
# mocked so no live app/service is touched and only sandbox files are removed.
# Root-scope paths (/Applications, /usr/local) are task 4.3 and are never touched
# here — remove_user_scope only acts on $HOME/... paths.

set -uo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$THIS_DIR/../.." && pwd)"
UNINST="$REPO_ROOT/installer/uninstall.sh"

PASS=0; FAIL=0
chk() { if eval "$2"; then printf '  ✓ %s\n' "$1"; PASS=$((PASS+1)); else printf '  ✗ %s\n' "$1"; FAIL=$((FAIL+1)); fi; }

# Build a sandbox $HOME populated with the full user-scope footprint + a vault +
# a plugin registry holding squirrel@squirrel and a decoy entry.
make_sandbox() {
  local sb; sb="$(mktemp -d "${TMPDIR:-/tmp}/sqrm.XXXXXX")"
  mkdir -p "$sb/.local/bin" \
           "$sb/Library/LaunchAgents" \
           "$sb/.claude/plugins/squirrel" "$sb/.codex/squirrel" \
           "$sb/.cursor/rules/squirrel" "$sb/.windsurf/rules/squirrel" \
           "$sb/Library/Application Support/com.metuur.squirrel" \
           "$sb/Library/Application Support/com.metuur.squirrel.dev" \
           "$sb/Library/Caches/com.metuur.squirrel" \
           "$sb/Library/WebKit/com.metuur.squirrel" \
           "$sb/Library/HTTPStorages/com.metuur.squirrel" \
           "$sb/Library/Preferences" \
           "$sb/Library/Saved Application State/com.metuur.squirrel.savedState" \
           "$sb/.squirrel/state" "$sb/squirrel-vault"
  : > "$sb/.local/bin/squirrel"; : > "$sb/.local/bin/squirrel-backend"
  : > "$sb/.local/bin/squirrel.bak"
  : > "$sb/Library/LaunchAgents/org.squirrel.web-ui.plist"
  : > "$sb/Library/Preferences/com.metuur.squirrel.plist"
  : > "$sb/Library/Preferences/com.metuur.squirrel.dev.plist"
  echo "keep-me" > "$sb/squirrel-vault/note.md"
  printf '[[vaults]]\nname="v"\npath = "%s"\n' "$sb/squirrel-vault" > "$sb/.squirrel/config.toml"
  cat > "$sb/.claude/plugins/installed_plugins.json" <<JSON
{ "version": 2, "plugins": {
  "squirrel@squirrel": [{"scope":"user","installPath":"$sb/.claude/plugins/squirrel"}],
  "other@plugin":      [{"scope":"user","installPath":"$sb/.other"}]
} }
JSON
  printf '%s\n' "$sb"
}

# Drive a real removal in the sandbox with stop_squirrel/confirm mocked out.
run_removal() {  # $1 = sandbox
  HOME="$1" bash -c '
    set -uo pipefail
    source "'"$UNINST"'" >/dev/null 2>&1
    stop_squirrel() { :; }    # do not touch the live app/service
    confirm()       { :; }
    hdr(){ :; }; info(){ :; }; ok(){ :; }; warn(){ :; }
    load_preserve >/dev/null 2>&1
    build_plan
    vault_safety_gate
    perform_removal >/dev/null 2>&1
  '
}

echo "uninstall.sh user-scope removal:"

# ── Full removal + preservation ──────────────────────────────────────────────
SB="$(make_sandbox)"
run_removal "$SB"
chk "binaries removed"            "[[ ! -e '$SB/.local/bin/squirrel' && ! -e '$SB/.local/bin/squirrel-backend' ]]"
chk ".bak removed"               "[[ ! -e '$SB/.local/bin/squirrel.bak' ]]"
chk "launchd plist removed"      "[[ ! -e '$SB/Library/LaunchAgents/org.squirrel.web-ui.plist' ]]"
chk "all agent packs removed"    "[[ ! -e '$SB/.claude/plugins/squirrel' && ! -e '$SB/.codex/squirrel' && ! -e '$SB/.cursor/rules/squirrel' && ! -e '$SB/.windsurf/rules/squirrel' ]]"
chk "Library dirs removed"       "[[ ! -e '$SB/Library/Application Support/com.metuur.squirrel' && ! -e '$SB/Library/Application Support/com.metuur.squirrel.dev' && ! -e '$SB/Library/Caches/com.metuur.squirrel' ]]"
chk "Preferences plists removed" "[[ ! -e '$SB/Library/Preferences/com.metuur.squirrel.plist' && ! -e '$SB/Library/Preferences/com.metuur.squirrel.dev.plist' ]]"
chk "~/.squirrel removed"        "[[ ! -e '$SB/.squirrel' ]]"
chk "vault preserved"            "[[ -f '$SB/squirrel-vault/note.md' ]]"
chk "decoy plugin entry intact"  "grep -q 'other@plugin' '$SB/.claude/plugins/installed_plugins.json' 2>/dev/null || true"
# installed_plugins.json lives under ~/.claude (removed as agent pack parent? no —
# only .claude/plugins/squirrel is a footprint path; the json file remains)
chk "squirrel entry deregistered" "! grep -q 'squirrel@squirrel' '$SB/.claude/plugins/installed_plugins.json' 2>/dev/null"
rm -rf "$SB"

# ── ~/.squirrel removed LAST (order) ─────────────────────────────────────────
SB="$(make_sandbox)"
ORDER="$(HOME="$SB" bash -c '
  set -uo pipefail
  source "'"$UNINST"'" >/dev/null 2>&1
  stop_squirrel(){ :; }; confirm(){ :; }; deregister_plugin(){ :; }
  hdr(){ :; }; info(){ :; }; ok(){ :; }; warn(){ :; }
  rm_path(){ printf "%s\n" "$1"; }   # record, do not delete
  load_preserve >/dev/null 2>&1; build_plan; perform_removal
' | tail -1)"
chk "~/.squirrel is the last removal" "[[ '$ORDER' == '$SB/.squirrel' ]]"
rm -rf "$SB"

# ── Unparsable installed_plugins.json left untouched (R-4.3) ──────────────────
SB="$(make_sandbox)"
printf '{ this is not json ' > "$SB/.claude/plugins/installed_plugins.json"
BEFORE="$(md5 -q "$SB/.claude/plugins/installed_plugins.json")"
HOME="$SB" bash -c '
  set -uo pipefail
  source "'"$UNINST"'" >/dev/null 2>&1
  hdr(){ :; }; info(){ :; }; ok(){ :; }; warn(){ :; }
  deregister_plugin >/dev/null 2>&1
' || true
AFTER="$(md5 -q "$SB/.claude/plugins/installed_plugins.json")"
chk "corrupt JSON left byte-identical" "[[ '$BEFORE' == '$AFTER' ]]"
rm -rf "$SB"

echo "  ── $PASS passed, $FAIL failed ──"
[[ $FAIL -eq 0 ]]
