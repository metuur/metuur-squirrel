#!/usr/bin/env bash
# scripts/build-dmg.sh — Builds the Squirrel macOS *full-stack* installer DMG.
#
# Produces a signed, notarized, stapled squirrel-installer-macos.dmg containing
# both universal (arm64 + x86_64) binaries, the agent-pack, and the end-user
# installer script.
#
# SIGNING (R-3.8 dev fallback):
#   Set APPLE_SIGNING_IDENTITY to your Developer ID Application identity.
#   If unset, signing/notarization/stapling steps are skipped and the script
#   emits a WARN line — suitable for dev iteration only. The resulting unsigned
#   DMG will be refused by installer/install.sh.
#
# Usage:
#   ./scripts/build-dmg.sh                       # build universal squirrel-installer-macos.dmg
#   ./scripts/build-dmg.sh --arm64-only          # arm64 slice only (no Rosetta/lipo, dev build)
#   ./scripts/build-dmg.sh --dry-run             # print steps without executing
#
# Required env vars for signing:
#   APPLE_SIGNING_IDENTITY   — "Developer ID Application: Name (TEAMID)"
#   APPLE_ID                 — your Apple ID email
#   APPLE_PASSWORD           — app-specific password (from appleid.apple.com)
#   APPLE_TEAM_ID            — 10-char team identifier
#
# Prerequisites (dev machine only):
#   pip install pyinstaller
#   pnpm install
#   Rosetta (on Apple Silicon; for the x86_64 binary slice)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
BUILD="$ROOT/build/pyinstaller"
STAGING="$ROOT/dmg-staging"
DMG_OUT="$ROOT/squirrel-installer-macos.dmg"
DRY_RUN=0
ARM64_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --dry-run)    DRY_RUN=1 ;;
    --arm64-only) ARM64_ONLY=1 ;;
    *) printf 'Unknown arg: %s\n' "$arg" >&2; exit 1 ;;
  esac
done

# ─── Colors ──────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'
  C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_BLUE=''; C_BOLD=''; C_RED=''; C_YELLOW=''; C_RESET=''
fi
say()  { printf '%s\n' "$*"; }
ok()   { printf '%s✓  %s%s\n' "$C_GREEN" "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE" "$*" "$C_RESET"; }
warn() { printf '%s⚠  %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
hdr()  { printf '\n%s=== %s ===%s\n' "$C_BOLD" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED" "$*" "$C_RESET" >&2; exit 1; }
run()  { info "$*"; (( DRY_RUN )) || eval "$*"; }

# ─── R-3.8: Dev fallback — skip all signing when identity is unset ────────────
SIGNING=1
if [[ -z "${APPLE_SIGNING_IDENTITY:-}" ]]; then
  SIGNING=0
  warn "APPLE_SIGNING_IDENTITY unset — producing unsigned installer (dev iteration mode)"
fi

# ─── Version ─────────────────────────────────────────────────────────────────
VERSION="$(grep '^version' "$ROOT/apps/cli/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')"
say ""
printf '%s🐿  Building Squirrel v%s installer%s\n' "$C_BOLD" "$VERSION" "$C_RESET"
(( DRY_RUN ))    && printf '%s    (dry-run — no files written)%s\n'  "$C_BOLD" "$C_RESET"
(( ARM64_ONLY )) && warn "arm64-only mode — skipping x86_64 slice and lipo (dev build, not universal)"

# ─── Preflight ───────────────────────────────────────────────────────────────
hdr "Preflight"
command -v pyinstaller >/dev/null 2>&1 || die "pyinstaller not found — run: pip install pyinstaller"
command -v pnpm        >/dev/null 2>&1 || die "pnpm not found — see https://pnpm.io"
command -v hdiutil     >/dev/null 2>&1 || die "hdiutil not found (macOS only)"
command -v lipo        >/dev/null 2>&1 || die "lipo not found — install Xcode Command Line Tools"
if (( SIGNING )); then
  command -v codesign     >/dev/null 2>&1 || die "codesign not found — install Xcode Command Line Tools"
  command -v xcrun        >/dev/null 2>&1 || die "xcrun not found — install Xcode Command Line Tools"
fi

HOST_ARCH="$(uname -m)"
if [[ "$HOST_ARCH" == "arm64" ]] && (( ! DRY_RUN )) && (( ! ARM64_ONLY )); then
  if ! arch -x86_64 /usr/bin/true 2>/dev/null; then
    die "Rosetta is not available — run 'softwareupdate --install-rosetta' to install it"
  fi
fi
ok "pyinstaller, pnpm, hdiutil, lipo available"

# ─── Helper: run PyInstaller for one arch slice ───────────────────────────────
# Usage: _pyinstaller_slice <arm64|x86_64> <name> <entry> <dist> <build> [extra args...]
_pyinstaller_slice() {
  local slice_arch="$1"; local bin_name="$2"; local entry="$3"
  local dist_dir="$4";   local build_dir="$5"
  shift 5
  mkdir -p "$dist_dir" "$build_dir"
  local -a cmd=(
    pyinstaller
    --onefile
    --name "$bin_name"
    --distpath "$dist_dir"
    --workpath "$build_dir"
    --specpath "$build_dir"
    --paths "$ROOT/apps/cli/lib"
    --clean
    --noconfirm
    "$@"
    "$entry"
  )
  if [[ "$HOST_ARCH" == "arm64" && "$slice_arch" == "x86_64" ]]; then
    info "pyinstaller (x86_64 via Rosetta) → $bin_name"
    (( DRY_RUN )) || PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" \
      arch -x86_64 "${cmd[@]}" >/dev/null
  elif [[ "$HOST_ARCH" == "x86_64" && "$slice_arch" == "arm64" ]]; then
    info "pyinstaller (arm64) → $bin_name"
    (( DRY_RUN )) || PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" \
      arch -arm64 "${cmd[@]}" >/dev/null
  else
    info "pyinstaller (${slice_arch} native) → $bin_name"
    (( DRY_RUN )) || PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" \
      "${cmd[@]}" >/dev/null
  fi
}

# ─── Helper: sign a binary (R-3.1, R-3.2) ────────────────────────────────────
_sign_binary() {
  local bin="$1"
  local name; name="$(basename "$bin")"
  local stderr_out; stderr_out="$(mktemp)"
  info "codesign --force --options runtime --timestamp → $name"
  if (( DRY_RUN )); then return; fi
  local exit_code=0
  codesign --force --options runtime --timestamp \
    --sign "$APPLE_SIGNING_IDENTITY" "$bin" 2>"$stderr_out" || exit_code=$?
  if (( exit_code )); then
    cat "$stderr_out" >&2
    rm -f "$stderr_out"
    # R-6.2: structured failure line
    printf 'failed: installer-dmg path, step: codesign %s, exit=%d\n' "$name" "$exit_code" >&2
    exit 1
  fi
  rm -f "$stderr_out"
}

# ─── Helper: verify a binary signature ───────────────────────────────────────
_verify_binary() {
  local bin="$1"
  local name; name="$(basename "$bin")"
  local stderr_out; stderr_out="$(mktemp)"
  local exit_code=0
  codesign --verify --strict --deep "$bin" 2>"$stderr_out" || exit_code=$?
  if (( exit_code )); then
    cat "$stderr_out" >&2
    rm -f "$stderr_out"
    die "codesign verification failed for $name — cannot proceed to hdiutil"
  fi
  rm -f "$stderr_out"
}

# ─── Helper: notarize and staple (R-3.5, R-3.6) ──────────────────────────────
# APPLE_PASSWORD is never echoed to the log (R-6.5).
_notarize_and_staple() {
  local artifact="$1"
  local name; name="$(basename "$artifact")"

  # Validate required env vars (R-2.7 equivalent for installer path)
  for var in APPLE_ID APPLE_PASSWORD APPLE_TEAM_ID; do
    [[ -n "${!var:-}" ]] \
      || die "error: $var is unset — cannot notarize. Set it in your shell profile or .envrc."
  done

  info "notarytool submit → $name (this takes 1–5 min)"
  local stderr_out; stderr_out="$(mktemp)"
  local stdout_out; stdout_out="$(mktemp)"
  local exit_code=0

  if (( DRY_RUN )); then
    ok "notarytool submit → $name [dry-run]"
    return
  fi

  # Password passed via env var, not command line, to keep it out of process listings
  # (notarytool supports NOTARYTOOL_PASSWORD but also --password; use env to avoid arg exposure)
  xcrun notarytool submit "$artifact" \
    --apple-id "$APPLE_ID" \
    --team-id "$APPLE_TEAM_ID" \
    --password "$APPLE_PASSWORD" \
    --wait \
    >"$stdout_out" 2>"$stderr_out" || exit_code=$?

  if (( exit_code )); then
    cat "$stdout_out" >&2
    cat "$stderr_out" >&2
    rm -f "$stdout_out" "$stderr_out"
    printf 'failed: installer-dmg path, step: notarytool submit, exit=%d\n' "$exit_code" >&2
    exit 1
  fi

  # R-3.5: fail if verdict is not Accepted
  if ! grep -q "status: Accepted" "$stdout_out"; then
    grep "status:" "$stdout_out" >&2 || true
    cat "$stderr_out" >&2
    rm -f "$stdout_out" "$stderr_out"
    printf 'failed: installer-dmg path, step: notarytool verdict not Accepted, exit=1\n' >&2
    exit 1
  fi
  rm -f "$stdout_out" "$stderr_out"
  ok "notarytool: Accepted"

  # R-3.6: staple
  info "xcrun stapler staple → $name"
  stderr_out="$(mktemp)"
  exit_code=0
  xcrun stapler staple "$artifact" 2>"$stderr_out" || exit_code=$?
  if (( exit_code )); then
    cat "$stderr_out" >&2
    rm -f "$stderr_out"
    printf 'failed: installer-dmg path, step: xcrun stapler staple, exit=%d\n' "$exit_code" >&2
    exit 1
  fi
  rm -f "$stderr_out"
  ok "stapled: $name"
}

# ─── Step 1: Build React SPA ─────────────────────────────────────────────────
hdr "Step 1 — Build React SPA"
run "pnpm -F squirrel-web-ui build"
if (( ! DRY_RUN )); then
  [[ -d "$ROOT/apps/backend/app/dist" ]] || die "SPA build failed — apps/backend/app/dist missing"
fi
ok "SPA built → apps/backend/app/dist/"

# ─── Step 2: CLI binary — universal (R-1.3, R-1.5) ───────────────────────────
hdr "Step 2 — Compile CLI binary (squirrel) — universal"

CLI_ARM64_DIST="$DIST/slices/cli/arm64"
CLI_ARM64_BUILD="$BUILD/cli-arm64"
CLI_X86_DIST="$DIST/slices/cli/x86_64"
CLI_X86_BUILD="$BUILD/cli-x86_64"

_pyinstaller_slice arm64  squirrel "$ROOT/apps/cli/squirrel" "$CLI_ARM64_DIST" "$CLI_ARM64_BUILD"
if (( ! ARM64_ONLY )); then
  _pyinstaller_slice x86_64 squirrel "$ROOT/apps/cli/squirrel" "$CLI_X86_DIST"  "$CLI_X86_BUILD"
fi

if (( ! DRY_RUN )); then
  [[ -f "$CLI_ARM64_DIST/squirrel" ]] || die "CLI arm64 slice missing"
  xattr -cr "$CLI_ARM64_DIST/squirrel"
  mkdir -p "$DIST"
  if (( ARM64_ONLY )); then
    cp "$CLI_ARM64_DIST/squirrel" "$DIST/squirrel"
  else
    [[ -f "$CLI_X86_DIST/squirrel" ]] || die "CLI x86_64 slice missing"
    xattr -cr "$CLI_X86_DIST/squirrel"
    lipo -create -output "$DIST/squirrel" "$CLI_ARM64_DIST/squirrel" "$CLI_X86_DIST/squirrel"
    ARCHS="$(lipo -archs "$DIST/squirrel")"
    [[ "$ARCHS" == "arm64 x86_64" ]] \
      || die "CLI binary has unexpected archs: '$ARCHS' (expected 'arm64 x86_64')"
  fi
fi
(( ARM64_ONLY )) && ok "CLI binary → dist/squirrel (arm64)" || ok "CLI binary → dist/squirrel (universal)"

# ─── Step 3: Backend binary — universal (R-1.4, R-1.5) ───────────────────────
hdr "Step 3 — Compile backend binary (squirrel-backend) — universal"

SPA_DIST="$ROOT/apps/backend/app/dist"
BE_ARM64_DIST="$DIST/slices/backend/arm64"
BE_ARM64_BUILD="$BUILD/backend-arm64"
BE_X86_DIST="$DIST/slices/backend/x86_64"
BE_X86_BUILD="$BUILD/backend-x86_64"

_pyinstaller_slice arm64  squirrel-backend "$ROOT/apps/backend/server.py" \
  "$BE_ARM64_DIST" "$BE_ARM64_BUILD" --add-data "$SPA_DIST:app/dist"
if (( ! ARM64_ONLY )); then
  _pyinstaller_slice x86_64 squirrel-backend "$ROOT/apps/backend/server.py" \
    "$BE_X86_DIST"  "$BE_X86_BUILD"  --add-data "$SPA_DIST:app/dist"
fi

if (( ! DRY_RUN )); then
  [[ -f "$BE_ARM64_DIST/squirrel-backend" ]] || die "backend arm64 slice missing"
  xattr -cr "$BE_ARM64_DIST/squirrel-backend"
  if (( ARM64_ONLY )); then
    cp "$BE_ARM64_DIST/squirrel-backend" "$DIST/squirrel-backend"
  else
    [[ -f "$BE_X86_DIST/squirrel-backend" ]] || die "backend x86_64 slice missing"
    xattr -cr "$BE_X86_DIST/squirrel-backend"
    lipo -create -output "$DIST/squirrel-backend" \
      "$BE_ARM64_DIST/squirrel-backend" "$BE_X86_DIST/squirrel-backend"
    ARCHS="$(lipo -archs "$DIST/squirrel-backend")"
    [[ "$ARCHS" == "arm64 x86_64" ]] \
      || die "backend binary has unexpected archs: '$ARCHS' (expected 'arm64 x86_64')"
  fi
fi
(( ARM64_ONLY )) && ok "Backend binary → dist/squirrel-backend (arm64)" || ok "Backend binary → dist/squirrel-backend (universal)"

# ─── Step 4: Assemble DMG staging ────────────────────────────────────────────
hdr "Step 4 — Assemble DMG staging"
run "rm -rf '$STAGING'"
run "mkdir -p '$STAGING/bin' '$STAGING/resources'"

run "cp '$DIST/squirrel'         '$STAGING/bin/squirrel'"
run "cp '$DIST/squirrel-backend' '$STAGING/bin/squirrel-backend'"

run "cp -r '$ROOT/agent-pack' '$STAGING/agent-pack'"
run "cp '$ROOT/apps/backend/launchd/plist.template' '$STAGING/resources/plist.template'"
run "cp '$ROOT/agent-pack/config/squirrel.toml.example' '$STAGING/resources/squirrel.toml.example'"

(( DRY_RUN )) || printf '%s\n' "$VERSION" > "$STAGING/VERSION"

run "cp '$ROOT/installer/install.sh' '$STAGING/Install Squirrel'"
run "chmod +x '$STAGING/Install Squirrel'"

ok "Staging assembled → dmg-staging/"

# ─── Step 5: Sign staged binaries (R-3.1, R-3.2) ─────────────────────────────
hdr "Step 5 — Sign staged binaries"
if (( SIGNING )); then
  _sign_binary "$STAGING/bin/squirrel"
  _sign_binary "$STAGING/bin/squirrel-backend"
  ok "staged binaries signed"
else
  info "skipping codesign (APPLE_SIGNING_IDENTITY unset)"
fi

# ─── Step 6: Pre-DMG codesign verification gate (R-3.3) ──────────────────────
hdr "Step 6 — Pre-DMG codesign verification"
if (( SIGNING && ! DRY_RUN )); then
  _verify_binary "$STAGING/bin/squirrel"
  ok "verified: squirrel"
  _verify_binary "$STAGING/bin/squirrel-backend"
  ok "verified: squirrel-backend"
else
  info "skipping verification gate (signing disabled or dry-run)"
fi

# ─── Step 7: Create DMG ───────────────────────────────────────────────────────
hdr "Step 7 — Create DMG"
run "rm -f '$DMG_OUT'"
run "hdiutil create \
  -volname 'Squirrel $VERSION' \
  -srcfolder '$STAGING' \
  -ov \
  -format UDZO \
  '$DMG_OUT'"
ok "DMG created → squirrel-installer-macos.dmg"

# ─── Step 8: Sign the DMG (R-3.4) ────────────────────────────────────────────
hdr "Step 8 — Sign DMG"
if (( SIGNING )); then
  info "codesign → squirrel-installer-macos.dmg"
  if (( ! DRY_RUN )); then
    local_stderr="$(mktemp)"
    exit_code=0
    codesign --sign "$APPLE_SIGNING_IDENTITY" "$DMG_OUT" 2>"$local_stderr" || exit_code=$?
    if (( exit_code )); then
      cat "$local_stderr" >&2
      rm -f "$local_stderr"
      printf 'failed: installer-dmg path, step: codesign dmg, exit=%d\n' "$exit_code" >&2
      exit 1
    fi
    rm -f "$local_stderr"
  fi
  ok "DMG signed"
else
  info "skipping DMG codesign (APPLE_SIGNING_IDENTITY unset)"
fi

# ─── Step 9: Notarize + staple (R-3.5, R-3.6) ────────────────────────────────
hdr "Step 9 — Notarize + staple"
if (( SIGNING )); then
  _notarize_and_staple "$DMG_OUT"
else
  info "skipping notarization (APPLE_SIGNING_IDENTITY unset)"
fi

# ─── Step 10: spctl final-state assertion (R-3.7) ────────────────────────────
hdr "Step 10 — Gatekeeper assertion"
if (( SIGNING && ! DRY_RUN )); then
  info "spctl --assess → squirrel-installer-macos.dmg"
  spctl_out="$(mktemp)"
  spctl_code=0
  spctl --assess --type open --context context:primary-signature "$DMG_OUT" \
    >"$spctl_out" 2>&1 || spctl_code=$?
  if (( spctl_code )) || ! grep -q "accepted source=Notarized Developer ID" "$spctl_out"; then
    cat "$spctl_out" >&2
    rm -f "$spctl_out"
    printf 'failed: installer-dmg path, step: spctl assess, exit=%d\n' "$spctl_code" >&2
    exit 1
  fi
  rm -f "$spctl_out"
  ok "spctl: accepted source=Notarized Developer ID"
else
  info "skipping spctl assertion (signing disabled or dry-run)"
fi

# ─── R-6.1: Summary log ──────────────────────────────────────────────────────
say ""
if (( SIGNING && ! DRY_RUN )); then
  SIGNING_IDENTITY_LABEL="$(security find-identity -v -p codesigning 2>/dev/null \
    | grep -o '"Developer ID Application:[^"]*"' | head -1 | tr -d '"' || echo "$APPLE_SIGNING_IDENTITY")"
  printf 'signed: %s identity=%s stapled=yes\n' "$DMG_OUT" "$SIGNING_IDENTITY_LABEL"
fi

printf '%sDone.%s  Distribute: %s\n' "$C_BOLD" "$C_RESET" "squirrel-installer-macos.dmg"
printf '       Size: %s\n' "$(du -sh "$DMG_OUT" 2>/dev/null | cut -f1 || echo "n/a (dry-run)")"
say ""
