#!/usr/bin/env bash
#
# apps/desktop/scripts/tauri-build.sh
#
# Wrapper around `pnpm tauri build -- --target universal-apple-darwin` that
# guards against missing signing credentials before cargo starts.
#
# Signing behaviour (R-2.6, R-2.7, R-2.8):
#   - No Developer ID Application cert in keychain → exit 1, no cargo build
#   - APPLE_ID / APPLE_PASSWORD / APPLE_TEAM_ID unset → exit 1, no cargo build
#   - APPLE_SIGNING_IDENTITY unset → WARN, build proceeds unsigned (dev mode)
#
# All other args are forwarded to `pnpm tauri build`, so:
#   pnpm tauri:build               → universal signed build
#   pnpm tauri:build -- --debug    → universal signed debug build

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_ROOT="$(cd "$HERE/.." && pwd)"

if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_BLUE=$'\033[34m'; C_RED=$'\033[31m'
  C_YELLOW=$'\033[33m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_BLUE=''; C_RED=''; C_YELLOW=''; C_BOLD=''; C_RESET=''
fi
ok()   { printf '%s✓  %s%s\n' "$C_GREEN"  "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE"   "$*" "$C_RESET"; }
warn() { printf '%s⚠  %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED"    "$*" "$C_RESET" >&2; exit 1; }

# ─── Signing mode ─────────────────────────────────────────────────────────────
SIGNING=1
if [[ -z "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  # R-2.8: APPLE_SIGNING_IDENTITY unset → unsigned dev build
  SIGNING=0
  warn "APPLE_SIGNING_IDENTITY unset — producing unsigned bundle (dev iteration mode)"
fi

if (( SIGNING )); then
  # R-2.6: Developer ID Application cert must be in the keychain
  if ! security find-identity -v -p codesigning 2>/dev/null \
      | grep -q "Developer ID Application:"; then
    die "error: no Developer ID Application identity in keychain — see docs/release.md for enrollment"
  fi

  # R-2.7: notarization env vars must be set
  for var in APPLE_ID APPLE_PASSWORD APPLE_TEAM_ID; do
    [[ -n "${!var:-}" ]] \
      || die "error: $var is unset — set it in your shell profile or .envrc before signing"
  done

  ok "signing identity: $APPLE_SIGNING_IDENTITY"
fi

# ─── Build ────────────────────────────────────────────────────────────────────
info "running: pnpm tauri build -- --target universal-apple-darwin $*"
cd "$DESKTOP_ROOT"
pnpm tauri build -- --target universal-apple-darwin "$@"
BUILD_EXIT=$?

if (( BUILD_EXIT )); then
  printf 'failed: tauri-path, step: pnpm tauri build, exit=%d\n' "$BUILD_EXIT" >&2
  exit "$BUILD_EXIT"
fi

# ─── R-6.1: Summary log (Tauri path) ─────────────────────────────────────────
if (( SIGNING )); then
  APP="$DESKTOP_ROOT/src-tauri/target/universal-apple-darwin/release/bundle/macos/Squirrel.app"
  DMG_GLOB=("$DESKTOP_ROOT"/src-tauri/target/universal-apple-darwin/release/bundle/dmg/Squirrel_*_universal.dmg)

  IDENTITY="$(security find-identity -v -p codesigning 2>/dev/null \
    | grep -o '"Developer ID Application:[^"]*"' | head -1 | tr -d '"' \
    || echo "$APPLE_SIGNING_IDENTITY")"

  [[ -d "$APP" ]] \
    && printf 'signed: %s identity=%s stapled=yes\n' "$APP" "$IDENTITY"

  for dmg in "${DMG_GLOB[@]}"; do
    [[ -f "$dmg" ]] \
      && printf 'signed: %s identity=%s stapled=yes\n' "$dmg" "$IDENTITY"
  done
fi
