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
REPO_ROOT="$(cd "$DESKTOP_ROOT/../.." && pwd)"

# Build target. Defaults to a universal (arm64 + x86_64) binary; override with
# e.g. TAURI_TARGET=aarch64-apple-darwin for an Apple-Silicon-only build.
TARGET="${TAURI_TARGET:-universal-apple-darwin}"

# For an Apple-Silicon-only build, tell the sidecar builder to skip the x86_64
# slice + universal lipo and emit a host-triple-named arm64 binary (which is
# what Tauri's externalBin resolution looks for at this target). Propagates to
# the beforeBundleCommand (`pnpm tauri:prebuild-backend`) as a child process.
if [[ "$TARGET" == "aarch64-apple-darwin" ]]; then
  export SQUIRREL_ARM64_ONLY=1
fi

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
info "running: pnpm tauri build -- --target $TARGET $*"
cd "$DESKTOP_ROOT"
# Don't let set -e abort before we can inspect the result: Tauri's DMG
# Finder-window AppleScript step can exit non-zero in a headless/non-GUI context
# AFTER both artifacts are already built, signed, and (for the .app) notarized.
set +e
pnpm tauri build -- --target "$TARGET" "$@"
BUILD_EXIT=$?
set -e

# ─── Locate artifacts (robust to workspace target layout) ─────────────────────
# Cargo workspace places target/ at the repo root; Tauri may emit the bundle at
# either target/release/bundle or target/<triple>/release/bundle. Discover it.
APP="$(find "$REPO_ROOT/target" -type d -name 'Squirrel.app' -path '*/bundle/macos/*' 2>/dev/null | head -1 || true)"
DMG="$(find "$REPO_ROOT/target" -type f -name 'Squirrel_*.dmg'  -path '*/bundle/dmg/*'  2>/dev/null | head -1 || true)"

# Treat the build as failed only if the .app was not produced. A non-zero exit
# with artifacts present is the cosmetic DMG-window step — warn and continue.
if [[ -z "$APP" || ! -d "$APP" ]]; then
  printf 'failed: tauri-path, step: pnpm tauri build, exit=%d (no Squirrel.app produced)\n' "$BUILD_EXIT" >&2
  exit "$(( BUILD_EXIT == 0 ? 1 : BUILD_EXIT ))"
fi
if (( BUILD_EXIT )); then
  warn "tauri exited $BUILD_EXIT but artifacts were produced — treating as success (cosmetic DMG window step)"
fi

# ─── Notarize + staple the DMG ───────────────────────────────────────────────
# Tauri notarizes and staples the .app, but only *signs* the .dmg. Notarize and
# staple the .dmg too so the download mounts without a Gatekeeper warning.
if (( SIGNING )) && [[ -n "$DMG" && -f "$DMG" ]]; then
  if xcrun stapler validate "$DMG" >/dev/null 2>&1; then
    ok "DMG already stapled: $DMG"
  else
    info "notarizing DMG (Tauri signs but does not notarize it)..."
    NOTARIZE_OUT="$(xcrun notarytool submit "$DMG" \
      --apple-id "$APPLE_ID" --password "$APPLE_PASSWORD" --team-id "$APPLE_TEAM_ID" \
      --wait 2>&1)"
    printf '%s\n' "$NOTARIZE_OUT"
    grep -q 'status: Accepted' <<< "$NOTARIZE_OUT" \
      || die "DMG notarization did not return Accepted — see output above"
    xcrun stapler staple "$DMG" \
      || die "DMG stapling failed after a successful notarization"
    ok "DMG notarized + stapled"
  fi
fi

# ─── R-6.1: Summary log (Tauri path) ─────────────────────────────────────────
if (( SIGNING )); then
  IDENTITY="$(security find-identity -v -p codesigning 2>/dev/null \
    | grep -o '"Developer ID Application:[^"]*"' | head -1 | tr -d '"' \
    || echo "$APPLE_SIGNING_IDENTITY")"

  [[ -d "$APP" ]] \
    && printf 'signed: %s identity=%s stapled=yes\n' "$APP" "$IDENTITY"
  [[ -n "$DMG" && -f "$DMG" ]] \
    && printf 'signed: %s identity=%s stapled=yes\n' "$DMG" "$IDENTITY"
fi
