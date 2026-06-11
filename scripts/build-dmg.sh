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
#   ./scripts/build-dmg.sh                       # universal → squirrel-installer-macos.dmg
#   ./scripts/build-dmg.sh --arm64-only          # Apple Silicon → squirrel-installer-macos-arm64.dmg
#   ./scripts/build-dmg.sh --x86-only            # Intel (run on Intel host) → …-x86_64.dmg
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
# DMG_OUT is resolved after arg parsing — single-arch builds get an arch suffix
# (-arm64 / -x86_64) so the two installers don't overwrite each other; the
# universal build keeps the canonical squirrel-installer-macos.dmg name.
# Hardened-runtime entitlements for the PyInstaller --onefile binaries. Without
# com.apple.security.cs.disable-library-validation the extracted libpython fails
# to dlopen ("different Team IDs") and the backend crash-loops. See the plist.
ENTITLEMENTS="$ROOT/apps/desktop/src-tauri/Entitlements.plist"
DRY_RUN=0
ARM64_ONLY=0
X86_ONLY=0
SKIP_DMG=0   # --skip-dmg: build the SPA + dist/ CLI binaries, then stop before
             # assembling the manual drag-install .dmg. Used by `make build-pkg`,
             # which only needs dist/ and ships the .pkg-in-DMG instead.

for arg in "$@"; do
  case "$arg" in
    --dry-run)         DRY_RUN=1 ;;
    --arm64-only)      ARM64_ONLY=1 ;;
    --x86-only|--intel) X86_ONLY=1 ;;
    --skip-dmg)        SKIP_DMG=1 ;;
    *) printf 'Unknown arg: %s\n' "$arg" >&2; exit 1 ;;
  esac
done

if (( ARM64_ONLY && X86_ONLY )); then
  printf 'error: --arm64-only and --x86-only are mutually exclusive\n' >&2
  exit 1
fi

# ─── Version ─────────────────────────────────────────────────────────────────
VERSION="$(grep '^version' "$ROOT/apps/cli/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')"

# Arch-suffixed output for single-arch installers; canonical name for universal.
if (( ARM64_ONLY )); then
  DMG_OUT="$ROOT/squirrel-installer-macos-v${VERSION}-arm64.dmg"
elif (( X86_ONLY )); then
  DMG_OUT="$ROOT/squirrel-installer-macos-v${VERSION}-x86_64.dmg"
else
  DMG_OUT="$ROOT/squirrel-installer-macos-v${VERSION}.dmg"
fi
DMG_NAME="$(basename "$DMG_OUT")"

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

say ""
printf '%s🐿  Building Squirrel v%s installer%s\n' "$C_BOLD" "$VERSION" "$C_RESET"
(( DRY_RUN ))    && printf '%s    (dry-run — no files written)%s\n'  "$C_BOLD" "$C_RESET"
(( ARM64_ONLY )) && warn "arm64-only mode — Apple Silicon installer ($DMG_NAME); no x86_64 slice or lipo"
(( X86_ONLY ))   && warn "x86_64-only mode — Intel installer ($DMG_NAME); no arm64 slice or lipo"

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
# Rosetta is only needed to cross-build the x86_64 slice on Apple Silicon, which
# only happens for a universal build. Single-arch builds are native to their host.
if [[ "$HOST_ARCH" == "arm64" ]] && (( ! DRY_RUN )) && (( ! ARM64_ONLY )) && (( ! X86_ONLY )); then
  if ! arch -x86_64 /usr/bin/true 2>/dev/null; then
    die "Rosetta is not available — run 'softwareupdate --install-rosetta' to install it"
  fi
fi
# An Intel-only installer must be built on an Intel host (native x86_64 Python);
# cross-building it on Apple Silicon silently yields an arm64 slice (lipo's twin).
if (( X86_ONLY )) && (( ! DRY_RUN )) && [[ "$HOST_ARCH" != "x86_64" ]]; then
  die "error: --x86-only requires an Intel host (got $HOST_ARCH). Build the Intel installer on an Intel Mac or x86_64 CI runner."
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
  info "codesign --force --options runtime --timestamp --entitlements → $name"
  if (( DRY_RUN )); then return; fi
  local exit_code=0
  codesign --force --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS" \
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

  # Credentials: prefer a keychain profile so the app-specific password never
  # appears in the process listing ('ps'). Fall back to APPLE_ID/PASSWORD/TEAM_ID.
  #   one-time setup:  xcrun notarytool store-credentials <profile> \
  #                      --apple-id <id> --team-id <team> --password <app-specific-pwd>
  #   then:            export APPLE_KEYCHAIN_PROFILE=<profile>
  local -a notary_creds
  if [[ -n "${APPLE_KEYCHAIN_PROFILE:-}" ]]; then
    notary_creds=(--keychain-profile "$APPLE_KEYCHAIN_PROFILE")
  else
    for var in APPLE_ID APPLE_PASSWORD APPLE_TEAM_ID; do
      [[ -n "${!var:-}" ]] \
        || die "error: $var is unset — cannot notarize. Set it (or APPLE_KEYCHAIN_PROFILE) in your shell profile or .envrc."
    done
    notary_creds=(--apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD")
    warn "--password is passed on the command line (visible via 'ps'); set APPLE_KEYCHAIN_PROFILE to avoid this"
  fi

  info "notarytool submit → $name (Apple scan; usually 1–5 min)"
  local stderr_out; stderr_out="$(mktemp)"
  local stdout_out; stdout_out="$(mktemp)"
  local exit_code=0

  if (( DRY_RUN )); then
    ok "notarytool submit → $name [dry-run]"
    return
  fi

  # Run --wait in the background and print an elapsed-time heartbeat so the step
  # never looks frozen while Apple is scanning.
  xcrun notarytool submit "$artifact" "${notary_creds[@]}" --wait \
    >"$stdout_out" 2>"$stderr_out" &
  local notary_pid=$!
  SECONDS=0
  local warned_long=0
  while kill -0 "$notary_pid" 2>/dev/null; do
    sleep 10
    printf '%s   ⏳ notarizing… %dm%02ds elapsed%s\r' \
      "$C_BLUE" "$(( SECONDS / 60 ))" "$(( SECONDS % 60 ))" "$C_RESET"
    if (( SECONDS >= 1200 && warned_long == 0 )); then
      warned_long=1
      printf '\n'
      warn "20+ min elapsed — Apple's notarization queue may be backed up; still waiting…"
    fi
  done
  printf '\n'
  wait "$notary_pid" || exit_code=$?

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

# ─── Step 2: CLI binary (R-1.3, R-1.5) ───────────────────────────────────────
if (( ARM64_ONLY ));   then BUILD_KIND="arm64"
elif (( X86_ONLY ));   then BUILD_KIND="x86_64"
else                        BUILD_KIND="universal"; fi
hdr "Step 2 — Compile CLI binary (squirrel) — $BUILD_KIND"

CLI_ARM64_DIST="$DIST/slices/cli/arm64"
CLI_ARM64_BUILD="$BUILD/cli-arm64"
CLI_X86_DIST="$DIST/slices/cli/x86_64"
CLI_X86_BUILD="$BUILD/cli-x86_64"

if (( ! X86_ONLY )); then
  _pyinstaller_slice arm64  squirrel "$ROOT/apps/cli/squirrel" "$CLI_ARM64_DIST" "$CLI_ARM64_BUILD"
fi
if (( ! ARM64_ONLY )); then
  _pyinstaller_slice x86_64 squirrel "$ROOT/apps/cli/squirrel" "$CLI_X86_DIST"  "$CLI_X86_BUILD"
fi

if (( ! DRY_RUN )); then
  mkdir -p "$DIST"
  if (( ARM64_ONLY )); then
    [[ -f "$CLI_ARM64_DIST/squirrel" ]] || die "CLI arm64 slice missing"
    xattr -cr "$CLI_ARM64_DIST/squirrel"
    cp "$CLI_ARM64_DIST/squirrel" "$DIST/squirrel"
  elif (( X86_ONLY )); then
    [[ -f "$CLI_X86_DIST/squirrel" ]] || die "CLI x86_64 slice missing"
    xattr -cr "$CLI_X86_DIST/squirrel"
    cp "$CLI_X86_DIST/squirrel" "$DIST/squirrel"
  else
    [[ -f "$CLI_ARM64_DIST/squirrel" ]] || die "CLI arm64 slice missing"
    [[ -f "$CLI_X86_DIST/squirrel" ]]   || die "CLI x86_64 slice missing"
    xattr -cr "$CLI_ARM64_DIST/squirrel" "$CLI_X86_DIST/squirrel"
    lipo -create -output "$DIST/squirrel" "$CLI_ARM64_DIST/squirrel" "$CLI_X86_DIST/squirrel"
    ARCHS="$(lipo -archs "$DIST/squirrel")"
    [[ "$ARCHS" == "arm64 x86_64" ]] \
      || die "CLI binary has unexpected archs: '$ARCHS' (expected 'arm64 x86_64')"
  fi
fi
ok "CLI binary → dist/squirrel ($BUILD_KIND)"

# ─── Step 3: Backend binary (R-1.4, R-1.5) ───────────────────────────────────
hdr "Step 3 — Compile backend binary (squirrel-backend) — $BUILD_KIND"

SPA_DIST="$ROOT/apps/backend/app/dist"
BE_ARM64_DIST="$DIST/slices/backend/arm64"
BE_ARM64_BUILD="$BUILD/backend-arm64"
BE_X86_DIST="$DIST/slices/backend/x86_64"
BE_X86_BUILD="$BUILD/backend-x86_64"

if (( ! X86_ONLY )); then
  _pyinstaller_slice arm64  squirrel-backend "$ROOT/apps/backend/server.py" \
    "$BE_ARM64_DIST" "$BE_ARM64_BUILD" --add-data "$SPA_DIST:app/dist"
fi
if (( ! ARM64_ONLY )); then
  _pyinstaller_slice x86_64 squirrel-backend "$ROOT/apps/backend/server.py" \
    "$BE_X86_DIST"  "$BE_X86_BUILD"  --add-data "$SPA_DIST:app/dist"
fi

if (( ! DRY_RUN )); then
  if (( ARM64_ONLY )); then
    [[ -f "$BE_ARM64_DIST/squirrel-backend" ]] || die "backend arm64 slice missing"
    xattr -cr "$BE_ARM64_DIST/squirrel-backend"
    cp "$BE_ARM64_DIST/squirrel-backend" "$DIST/squirrel-backend"
  elif (( X86_ONLY )); then
    [[ -f "$BE_X86_DIST/squirrel-backend" ]] || die "backend x86_64 slice missing"
    xattr -cr "$BE_X86_DIST/squirrel-backend"
    cp "$BE_X86_DIST/squirrel-backend" "$DIST/squirrel-backend"
  else
    [[ -f "$BE_ARM64_DIST/squirrel-backend" ]] || die "backend arm64 slice missing"
    [[ -f "$BE_X86_DIST/squirrel-backend" ]]   || die "backend x86_64 slice missing"
    xattr -cr "$BE_ARM64_DIST/squirrel-backend" "$BE_X86_DIST/squirrel-backend"
    lipo -create -output "$DIST/squirrel-backend" \
      "$BE_ARM64_DIST/squirrel-backend" "$BE_X86_DIST/squirrel-backend"
    ARCHS="$(lipo -archs "$DIST/squirrel-backend")"
    [[ "$ARCHS" == "arm64 x86_64" ]] \
      || die "backend binary has unexpected archs: '$ARCHS' (expected 'arm64 x86_64')"
  fi
fi
ok "Backend binary → dist/squirrel-backend ($BUILD_KIND)"

# --skip-dmg: dist/ binaries are now built; the caller (build-pkg.sh flow) does
# not want the manual drag-install DMG. Stop here before Step 4.
if (( SKIP_DMG )); then
  printf '\n%sDone (binaries only).%s  dist/squirrel, dist/squirrel-backend ready; skipped manual DMG.\n' "$C_BOLD" "$C_RESET"
  exit 0
fi

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
ok "DMG created → $DMG_NAME"

# ─── Step 8: Sign the DMG (R-3.4) ────────────────────────────────────────────
hdr "Step 8 — Sign DMG"
if (( SIGNING )); then
  info "codesign → $DMG_NAME"
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
  info "spctl --assess → $DMG_NAME"
  spctl_out="$(mktemp)"
  spctl_code=0
  # -v makes spctl print the "source=..." line. Note: spctl emits "accepted"
  # and "source=Notarized Developer ID" on SEPARATE lines, so match each token
  # independently rather than as one contiguous string.
  spctl --assess --type open --context context:primary-signature -v "$DMG_OUT" \
    >"$spctl_out" 2>&1 || spctl_code=$?

  # Distinguish the two real failure modes so the message is honest:
  #   (a) spctl itself rejected the DMG  → non-zero exit (genuine Gatekeeper fail)
  #   (b) spctl accepted but the source/text isn't what we expect → unexpected state
  reason=""
  if (( spctl_code )); then
    reason="spctl rejected the DMG (exit=$spctl_code) — not accepted by Gatekeeper"
  elif ! grep -q ": accepted" "$spctl_out"; then
    reason="spctl exit=0 but output is missing 'accepted' — unexpected assessment"
  elif ! grep -q "source=Notarized Developer ID" "$spctl_out"; then
    reason="accepted, but source is not 'Notarized Developer ID' (not notarized?)"
  fi
  if [[ -n "$reason" ]]; then
    cat "$spctl_out" >&2
    rm -f "$spctl_out"
    die "Gatekeeper assertion failed: $reason"
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

printf '%sDone.%s  Distribute: %s\n' "$C_BOLD" "$C_RESET" "$DMG_NAME"
printf '       Size: %s\n' "$(du -sh "$DMG_OUT" 2>/dev/null | cut -f1 || echo "n/a (dry-run)")"
say ""
