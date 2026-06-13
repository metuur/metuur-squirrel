#!/usr/bin/env bash
# tests/installer/test_uninstall_summary.sh
#
# Summary, shell-rc note, and tee logging for uninstall.sh (R-3.5, R-4.7, R-5.5).
# Runs in a sandbox $HOME with destructive ops mocked; only sandbox files and a
# /tmp uninstall log are created, both cleaned up.

set -uo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$THIS_DIR/../.." && pwd)"
UNINST="$REPO_ROOT/installer/uninstall.sh"

PASS=0; FAIL=0
report() { if [[ "$1" -eq 1 ]]; then printf '  ✓ %s\n' "$2"; PASS=$((PASS+1)); else printf '  ✗ %s\n' "$2"; FAIL=$((FAIL+1)); fi; }
has() { case "$1" in *"$2"*) return 0 ;; *) return 1 ;; esac; }

echo "uninstall.sh summary / rc-note / tee:"

# ── Summary lists removed count, preserved vault, and failures (R-3.5) ────────
SB="$(mktemp -d "${TMPDIR:-/tmp}/sqsum.XXXXXX")"
SUMMARY="$(HOME="$SB" bash -c '
  set -uo pipefail
  source "'"$UNINST"'" >/dev/null 2>&1
  C_GREEN=""; C_RESET=""
  PRESERVE=("/Users/me/squirrel-vault")
  REMOVED=("/a" "/b" "/c")
  FAILURES=("/usr/local/share/squirrel")
  print_summary 2>&1
')"
has "$SUMMARY" "Removed 3 item(s)"          && report 1 "summary reports removed count"  || report 0 "summary reports removed count"
has "$SUMMARY" "squirrel-vault"             && report 1 "summary lists preserved vault"  || report 0 "summary lists preserved vault"
has "$SUMMARY" "/usr/local/share/squirrel"  && report 1 "summary lists failures"         || report 0 "summary lists failures"
rm -rf "$SB"

# ── rc-file PATH note printed, file left byte-identical (R-4.7) ───────────────
SB="$(mktemp -d "${TMPDIR:-/tmp}/sqsum.XXXXXX")"
printf '# my zshrc\nexport PATH="%s/.local/bin:$PATH"\nalias x=ls\n' "$SB" > "$SB/.zshrc"
BEFORE="$(md5 -q "$SB/.zshrc")"
NOTE="$(HOME="$SB" bash -c 'source "'"$UNINST"'" >/dev/null 2>&1; check_rc_path_note 2>&1')"
AFTER="$(md5 -q "$SB/.zshrc")"
{ has "$NOTE" ".zshrc" && has "$NOTE" "left unchanged"; } && report 1 "rc PATH note is printed" || report 0 "rc PATH note is printed"
[[ "$BEFORE" == "$AFTER" ]] && report 1 "rc file left byte-identical" || report 0 "rc file left byte-identical"
printf 'alias x=ls\n' > "$SB/.zshrc"
NOTE2="$(HOME="$SB" bash -c 'source "'"$UNINST"'" >/dev/null 2>&1; check_rc_path_note 2>&1')"
[[ -z "$NOTE2" ]] && report 1 "no note when no PATH line" || report 0 "no note when no PATH line"
rm -rf "$SB"

# ── tee writes a /tmp uninstall log on a real (mocked) run (R-5.5) ────────────
SB="$(mktemp -d "${TMPDIR:-/tmp}/sqsum.XXXXXX")"
mkdir -p "$SB/.squirrel"
printf '[[vaults]]\nname="v"\npath="%s/squirrel-vault"\n' "$SB" > "$SB/.squirrel/config.toml"
HOME="$SB" bash -c '
  set -uo pipefail
  source "'"$UNINST"'" >/dev/null 2>&1
  stop_squirrel(){ :; }; confirm(){ :; }; remove_root_scope(){ :; }
  deregister_plugin(){ :; }; remove_user_scope(){ :; }
  rm_path(){ :; }                    # no real deletion
  DRY_RUN=0
  main >/dev/null 2>&1 || true
' || true
NEWLOG="$(ls -t /tmp/squirrel-uninstall-*.log 2>/dev/null | head -1)"
[[ -f "$NEWLOG" ]] && report 1 "tee created a /tmp uninstall log" || report 0 "tee created a /tmp uninstall log"
[[ -s "$NEWLOG" ]] && report 1 "uninstall log has content"        || report 0 "uninstall log has content"
[[ -n "$NEWLOG" ]] && rm -f "$NEWLOG"
rm -rf "$SB"

echo "  ── $PASS passed, $FAIL failed ──"
[[ $FAIL -eq 0 ]]
