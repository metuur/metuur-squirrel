#!/usr/bin/env bash
# tests/installer/test_uninstall_root_scope.sh
#
# Root-scope removal coverage for uninstall.sh (R-4.4): a single sudo batch only
# when a genuinely root-owned target exists; no sudo otherwise. The PLAN is set
# directly to controlled sandbox paths and sudo_rm_batch is mocked, so the real
# /Applications and /usr/local are never read and sudo is never invoked.

set -uo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$THIS_DIR/../.." && pwd)"
UNINST="$REPO_ROOT/installer/uninstall.sh"

PASS=0; FAIL=0
chk() { if eval "$2"; then printf '  ✓ %s\n' "$1"; PASS=$((PASS+1)); else printf '  ✗ %s\n' "$1"; FAIL=$((FAIL+1)); fi; }

# Run remove_root_scope with a controlled PLAN and a mocked sudo batch. HOME is
# set to an empty dir so the sandbox paths count as non-$HOME (root-scope).
# Echoes: "<sudo-call-count>|<space-separated sudo targets>".
run_root_scope() {  # $@ = PLAN entries
  local home; home="$(mktemp -d "${TMPDIR:-/tmp}/sqrs-home.XXXXXX")"
  HOME="$home" PLAN_ARGS="$*" bash -c '
    set -uo pipefail
    source "'"$UNINST"'" >/dev/null 2>&1
    hdr(){ :; }; info(){ :; }; ok(){ :; }; warn(){ :; }
    SUDO_CALLS=0; SUDO_TARGETS=""
    sudo_rm_batch() { SUDO_CALLS=$((SUDO_CALLS+1)); SUDO_TARGETS="$*"; return 0; }
    read -r -a PLAN <<< "$PLAN_ARGS"
    remove_root_scope >/dev/null 2>&1
    printf "%s|%s\n" "$SUDO_CALLS" "$SUDO_TARGETS"
  '
  rm -rf "$home"
}

echo "uninstall.sh root-scope removal:"

# ── Case 1: no root paths exist → no sudo, no error ──────────────────────────
OUT="$(run_root_scope "/tmp/does-not-exist-squirrel-xyz")"
chk "no existing root paths → sudo not called" "[[ '${OUT%%|*}' == '0' ]]"

# ── Case 2: user-removable path (writable parent) → removed directly, no sudo ─
SB="$(mktemp -d "${TMPDIR:-/tmp}/sqrs.XXXXXX")"
mkdir -p "$SB/app/Squirrel.app"; : > "$SB/app/Squirrel.app/marker"
OUT="$(run_root_scope "$SB/app/Squirrel.app")"
chk "user-removable target → sudo not called"  "[[ '${OUT%%|*}' == '0' ]]"
chk "user-removable target actually deleted"    "[[ ! -e '$SB/app/Squirrel.app' ]]"
rm -rf "$SB"

# ── Case 3: root-owned target (read-only parent) → one sudo batch ────────────
SB="$(mktemp -d "${TMPDIR:-/tmp}/sqrs.XXXXXX")"
mkdir -p "$SB/ro/squirrel.app"
chmod 500 "$SB/ro"            # parent not writable → user_can_remove == false
OUT="$(run_root_scope "$SB/ro/squirrel.app")"
chk "root-owned target → exactly one sudo batch" "[[ '${OUT%%|*}' == '1' ]]"
chk "sudo batch targets the path"                "[[ '${OUT#*|}' == *'$SB/ro/squirrel.app'* ]]"
chmod 700 "$SB/ro"; rm -rf "$SB"

# ── Case 4: two root-owned targets → still a SINGLE sudo batch ───────────────
SB="$(mktemp -d "${TMPDIR:-/tmp}/sqrs.XXXXXX")"
mkdir -p "$SB/ro1/a" "$SB/ro2/b"; chmod 500 "$SB/ro1" "$SB/ro2"
OUT="$(run_root_scope "$SB/ro1/a" "$SB/ro2/b")"
chk "two root targets → one sudo call (batched)" "[[ '${OUT%%|*}' == '1' ]]"
chk "batch includes both targets"                "[[ '${OUT#*|}' == *'$SB/ro1/a'* && '${OUT#*|}' == *'$SB/ro2/b'* ]]"
chmod 700 "$SB/ro1" "$SB/ro2"; rm -rf "$SB"

echo "  ── $PASS passed, $FAIL failed ──"
[[ $FAIL -eq 0 ]]
