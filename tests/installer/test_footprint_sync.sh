#!/usr/bin/env bash
# tests/installer/test_footprint_sync.sh
#
# Footprint inventory integrity (R-5.6, R-5.7):
#   * the SQUIRREL-FOOTPRINT-SYNC block must be byte-identical in
#     install-snapshot.sh and uninstall.sh (edit both copies together),
#   * every footprint entry is a literal path (no glob metacharacters),
#   * uninstall.sh never runs rm with a wildcard — only enumerated paths.

set -uo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$THIS_DIR/../.." && pwd)"
SNAP="$REPO_ROOT/installer/install-snapshot.sh"
UNINST="$REPO_ROOT/installer/uninstall.sh"

PASS=0; FAIL=0
report() { if [[ "$1" -eq 1 ]]; then printf '  ✓ %s\n' "$2"; PASS=$((PASS+1)); else printf '  ✗ %s\n' "$2"; FAIL=$((FAIL+1)); fi; }

# Path lines between the sync markers (ignores the markers, cat<<EOF and EOF).
extract_paths() {
  sed -n '/SQUIRREL-FOOTPRINT-SYNC >>>/,/<<< SQUIRREL-FOOTPRINT-SYNC/p' "$1" \
    | grep -E '^(/|\$HOME)'
}

echo "footprint sync integrity:"

SNAP_PATHS="$(extract_paths "$SNAP")"
UNINST_PATHS="$(extract_paths "$UNINST")"

[[ -n "$SNAP_PATHS" ]] && report 1 "snapshot footprint block is non-empty" || report 0 "snapshot footprint block is non-empty"
[[ -n "$UNINST_PATHS" ]] && report 1 "uninstall footprint block is non-empty" || report 0 "uninstall footprint block is non-empty"

if [[ "$SNAP_PATHS" == "$UNINST_PATHS" ]]; then
  report 1 "footprint blocks are byte-identical across both scripts"
else
  report 0 "footprint blocks are byte-identical across both scripts"
  printf '    --- diff ---\n'; diff <(printf '%s\n' "$SNAP_PATHS") <(printf '%s\n' "$UNINST_PATHS") | sed 's/^/    /'
fi

# Every footprint entry must be a literal path — no glob metacharacters.
if printf '%s\n' "$UNINST_PATHS" | grep -qE '[*?]|\['; then
  report 0 "footprint entries are literal (no globs)"
  printf '    offending:\n'; printf '%s\n' "$UNINST_PATHS" | grep -E '[*?]|\[' | sed 's/^/    /'
else
  report 1 "footprint entries are literal (no globs)"
fi

# uninstall.sh must never call rm with a wildcard (R-5.6). Inspect rm lines that
# are not comments and assert none contain a glob char.
RM_GLOBS="$(grep -nE '(^|[^#])/bin/rm ' "$UNINST" | grep -E '[*?]' || true)"
if [[ -z "$RM_GLOBS" ]]; then
  report 1 "no rm command uses a wildcard"
else
  report 0 "no rm command uses a wildcard"
  printf '%s\n' "$RM_GLOBS" | sed 's/^/    /'
fi

echo "  ── $PASS passed, $FAIL failed ──"
[[ $FAIL -eq 0 ]]
