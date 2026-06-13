#!/usr/bin/env bash
# tests/installer/test_uninstall_vault_gate.sh
#
# Regression test for the uninstall.sh vault safety gate (R-3.3, R-3.4, R-3.4a).
# Every case runs in a throwaway $HOME sandbox created with mktemp and is
# torn down afterwards — the real home directory is never read or written.
#
# Cases run in --dry-run: the gate executes before the dry-run exit, so the
# abort behavior is fully exercised without any deletion. (Unit 4's removal test
# extends the "normal vault survives" case to a real --yes run.)

set -uo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$THIS_DIR/../.." && pwd)"
UNINST="$REPO_ROOT/installer/uninstall.sh"

PASS=0; FAIL=0
ok()   { printf '  ✓ %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  ✗ %s\n' "$1"; FAIL=$((FAIL+1)); }

[[ -f "$UNINST" ]] || { echo "missing $UNINST"; exit 1; }

# Make a sandbox HOME with a config.toml pointing at the given vault path.
make_home() {  # $1 = vault path to write into config
  local sb; sb="$(mktemp -d "${TMPDIR:-/tmp}/sqgate.XXXXXX")"
  mkdir -p "$sb/.squirrel"
  printf '[[vaults]]\nname = "v"\npath = "%s"\n' "$1" > "$sb/.squirrel/config.toml"
  printf '%s\n' "$sb"
}

run_uninstall() {  # $1 = sandbox HOME ; echoes nothing, returns uninstall rc
  HOME="$1" bash "$UNINST" --dry-run >/dev/null 2>&1
}

# ─── Case A: vault is a symlink pointing INTO ~/.squirrel ─────────────────────
caseA() {
  local sb; sb="$(make_home "")"  # rewrite config after we know the link path
  mkdir -p "$sb/.squirrel/vaults/main"
  echo "keep-me" > "$sb/.squirrel/vaults/main/note.md"
  ln -s "$sb/.squirrel/vaults/main" "$sb/squirrel-vault"
  printf '[[vaults]]\nname = "v"\npath = "%s"\n' "$sb/squirrel-vault" > "$sb/.squirrel/config.toml"

  if run_uninstall "$sb"; then
    bad "A: symlinked-into-app-data vault should ABORT but exited 0"
  else
    ok "A: symlinked-into-app-data vault aborts"
  fi
  [[ -f "$sb/.squirrel/vaults/main/note.md" ]] && ok "A: vault note untouched" \
                                               || bad "A: vault note was lost"
  rm -rf "$sb"
}

# ─── Case B: vault lives literally inside ~/.squirrel ─────────────────────────
caseB() {
  local sb; sb="$(make_home "")"
  mkdir -p "$sb/.squirrel/myvault"
  echo "keep-me" > "$sb/.squirrel/myvault/note.md"
  printf '[[vaults]]\nname = "v"\npath = "%s"\n' "$sb/.squirrel/myvault" > "$sb/.squirrel/config.toml"

  if run_uninstall "$sb"; then
    bad "B: vault inside ~/.squirrel should ABORT but exited 0"
  else
    ok "B: vault inside ~/.squirrel aborts"
  fi
  [[ -f "$sb/.squirrel/myvault/note.md" ]] && ok "B: vault note untouched" \
                                           || bad "B: vault note was lost"
  rm -rf "$sb"
}

# ─── Case C: normal sibling vault — gate passes, nothing deleted ──────────────
caseC() {
  local sb; sb="$(make_home "")"
  mkdir -p "$sb/squirrel-vault"
  echo "keep-me" > "$sb/squirrel-vault/note.md"
  printf '[[vaults]]\nname = "v"\npath = "%s"\n' "$sb/squirrel-vault" > "$sb/.squirrel/config.toml"

  if run_uninstall "$sb"; then
    ok "C: normal sibling vault proceeds (no abort)"
  else
    bad "C: normal sibling vault unexpectedly aborted"
  fi
  [[ -f "$sb/squirrel-vault/note.md" ]] && ok "C: vault note survives" \
                                        || bad "C: vault note was lost"
  rm -rf "$sb"
}

echo "uninstall.sh vault safety gate:"
caseA
caseB
caseC

echo "  ── $PASS passed, $FAIL failed ──"
[[ $FAIL -eq 0 ]]
