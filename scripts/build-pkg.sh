#!/usr/bin/env bash
# scripts/build-pkg.sh — Builds the Squirrel all-in-one macOS .pkg installer.
#
# Produces squirrel-installer-macos.pkg: a guided, double-click installer that
# lays down the desktop app, the CLI binaries, and staged agent-pack, then runs
# a postinstall that configures the logged-in user (config, vault, agent-pack).
#
# Payload (root-owned):
#   /Applications/Squirrel.app
#   /usr/local/bin/{squirrel,squirrel-backend}
#   /usr/local/share/squirrel/{agent-pack,resources}
#
# SIGNING (optional — dev fallback like build-dmg.sh):
#   APPLE_SIGNING_IDENTITY    "Developer ID Application: …"  → signs Squirrel.app
#   APPLE_INSTALLER_IDENTITY  "Developer ID Installer: …"    → signs the .pkg
#                             (auto-detected from the keychain if unset)
#   APPLE_KEYCHAIN_PROFILE | APPLE_ID/APPLE_PASSWORD/APPLE_TEAM_ID → notarization
#   With none set: an UNSIGNED .pkg is produced (dev only; Gatekeeper will block).
#
# Usage:
#   ./scripts/build-pkg.sh                 # build inputs as needed, then package
#   ./scripts/build-pkg.sh --skip-build    # reuse existing app + dist/ binaries
#   ./scripts/build-pkg.sh --dry-run       # print steps without executing
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
PKG_SRC="$ROOT/installer/pkg"
STAGING="$ROOT/pkg-staging"          # payload root
BUILD="$ROOT/build/pkg"              # intermediate component pkg + distribution.xml
PKG_OUT="$ROOT/squirrel-installer-macos.pkg"
APP_ID="com.metuur.squirrel"
SKIP_BUILD=0
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=1 ;;
    --dry-run)    DRY_RUN=1 ;;
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
ok()   { printf '%s✓  %s%s\n' "$C_GREEN" "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE" "$*" "$C_RESET"; }
warn() { printf '%s⚠  %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
hdr()  { printf '\n%s=== %s ===%s\n' "$C_BOLD" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED" "$*" "$C_RESET" >&2; exit 1; }
run()  { info "$*"; (( DRY_RUN )) || eval "$*"; }

# ─── Signing config ──────────────────────────────────────────────────────────
SIGN_APP=1
[[ -z "${APPLE_SIGNING_IDENTITY:-}" ]] && { SIGN_APP=0; warn "APPLE_SIGNING_IDENTITY unset — app will not be (re)signed"; }

# Resolve an Installer identity: explicit env, else auto-detect from keychain.
INSTALLER_ID="${APPLE_INSTALLER_IDENTITY:-}"
if [[ -z "$INSTALLER_ID" ]]; then
  INSTALLER_ID="$(security find-identity -v 2>/dev/null \
    | grep -o '"Developer ID Installer:[^"]*"' | head -1 | tr -d '"' || true)"
fi
SIGN_PKG=1
[[ -z "$INSTALLER_ID" ]] && { SIGN_PKG=0; warn "no Developer ID Installer identity — producing an UNSIGNED .pkg (dev only)"; }

# ─── Version ─────────────────────────────────────────────────────────────────
VERSION="$(grep '^version' "$ROOT/apps/cli/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')"
printf '\n%s🐿  Building Squirrel v%s .pkg installer%s\n' "$C_BOLD" "$VERSION" "$C_RESET"
(( DRY_RUN )) && printf '%s    (dry-run — no files written)%s\n' "$C_BOLD" "$C_RESET"

# ─── Preflight ───────────────────────────────────────────────────────────────
hdr "Preflight"
command -v pkgbuild     >/dev/null 2>&1 || die "pkgbuild not found (macOS only)"
command -v productbuild >/dev/null 2>&1 || die "productbuild not found (macOS only)"
ok "pkgbuild, productbuild available"

# ─── Locate / build inputs ───────────────────────────────────────────────────
hdr "Locate inputs (app + CLI binaries)"

APP=""
for cand in \
  "$ROOT/target/release/bundle/macos/Squirrel.app" \
  "$ROOT/apps/desktop/src-tauri/target/release/bundle/macos/Squirrel.app"; do
  [[ -d "$cand" ]] && { APP="$cand"; break; }
done

if [[ -z "$APP" ]]; then
  (( SKIP_BUILD )) && die "Squirrel.app not found and --skip-build set. Run: make build"
  run "( cd '$ROOT/apps/desktop' && pnpm tauri build )"
  for cand in \
    "$ROOT/target/release/bundle/macos/Squirrel.app" \
    "$ROOT/apps/desktop/src-tauri/target/release/bundle/macos/Squirrel.app"; do
    [[ -d "$cand" ]] && { APP="$cand"; break; }
  done
  [[ -n "$APP" || $DRY_RUN -eq 1 ]] || die "build finished but Squirrel.app still not found"
fi
[[ -n "$APP" ]] && ok "app → ${APP#$ROOT/}"

if [[ ! -f "$DIST/squirrel" || ! -f "$DIST/squirrel-backend" ]]; then
  (( SKIP_BUILD )) && die "dist/ binaries missing and --skip-build set. Run: make build-installers-arm64"
  die "dist/squirrel{,-backend} missing — run 'make build-installers-arm64' first (builds the CLI binaries)"
fi
ok "binaries → dist/squirrel, dist/squirrel-backend"

# ─── Sign the app (Developer ID Application) ─────────────────────────────────
hdr "Sign Squirrel.app"
if (( SIGN_APP )); then
  run "codesign --force --options runtime --timestamp --deep --sign '$APPLE_SIGNING_IDENTITY' '$APP'"
  (( DRY_RUN )) || codesign --verify --strict "$APP" || die "app signature verification failed"
  ok "app signed + verified"
else
  info "skipping app signing (APPLE_SIGNING_IDENTITY unset)"
fi

# ─── Assemble payload root ───────────────────────────────────────────────────
hdr "Assemble payload"
run "rm -rf '$STAGING' '$BUILD'"
run "mkdir -p '$STAGING/Applications' '$STAGING/usr/local/bin' '$STAGING/usr/local/share/squirrel/resources' '$BUILD'"

run "cp -R '$APP' '$STAGING/Applications/Squirrel.app'"
run "cp '$DIST/squirrel'         '$STAGING/usr/local/bin/squirrel'"
run "cp '$DIST/squirrel-backend' '$STAGING/usr/local/bin/squirrel-backend'"
run "chmod +x '$STAGING/usr/local/bin/squirrel' '$STAGING/usr/local/bin/squirrel-backend'"

run "cp -R '$ROOT/agent-pack' '$STAGING/usr/local/share/squirrel/agent-pack'"
run "cp '$ROOT/agent-pack/config/squirrel.toml.example' '$STAGING/usr/local/share/squirrel/resources/squirrel.toml.example'"
ok "payload → pkg-staging/"

# ─── pkgbuild: component package ──────────────────────────────────────────────
hdr "pkgbuild — component package"
COMPONENT="$BUILD/squirrel-component.pkg"
run "pkgbuild \
  --root '$STAGING' \
  --identifier '$APP_ID' \
  --version '$VERSION' \
  --scripts '$PKG_SRC/scripts' \
  --install-location / \
  '$COMPONENT'"
ok "component → ${COMPONENT#$ROOT/}"

# ─── productbuild: distribution (the GUI installer) ──────────────────────────
hdr "productbuild — distribution installer"
DISTXML="$BUILD/distribution.xml"
if (( ! DRY_RUN )); then
  sed "s/__VERSION__/$VERSION/g" "$PKG_SRC/distribution.xml.template" > "$DISTXML"
fi
UNSIGNED="$BUILD/squirrel-unsigned.pkg"
run "productbuild \
  --distribution '$DISTXML' \
  --package-path '$BUILD' \
  --resources '$PKG_SRC/resources' \
  '$UNSIGNED'"
ok "product → ${UNSIGNED#$ROOT/}"

# ─── Sign the product (Developer ID Installer) ───────────────────────────────
hdr "Sign .pkg"
run "rm -f '$PKG_OUT'"
if (( SIGN_PKG )); then
  run "productsign --sign '$INSTALLER_ID' '$UNSIGNED' '$PKG_OUT'"
  ok "pkg signed → ${PKG_OUT#$ROOT/}"
else
  run "cp '$UNSIGNED' '$PKG_OUT'"
  info "unsigned .pkg copied → ${PKG_OUT#$ROOT/}"
fi

# ─── Notarize + staple ───────────────────────────────────────────────────────
hdr "Notarize + staple"
if (( SIGN_PKG && ! DRY_RUN )); then
  # Credentials: prefer a keychain profile (keeps the app-specific password out
  # of the process listing). Fall back to APPLE_ID/PASSWORD/TEAM_ID env vars.
  notary_creds=()
  if [[ -n "${APPLE_KEYCHAIN_PROFILE:-}" ]]; then
    notary_creds=(--keychain-profile "$APPLE_KEYCHAIN_PROFILE")
  elif [[ -n "${APPLE_ID:-}" && -n "${APPLE_PASSWORD:-}" && -n "${APPLE_TEAM_ID:-}" ]]; then
    notary_creds=(--apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD")
    warn "--password passed on the command line (visible via 'ps'); set APPLE_KEYCHAIN_PROFILE to avoid this"
  else
    warn "no notarization credentials — signed but NOT notarized (set APPLE_KEYCHAIN_PROFILE or APPLE_ID/PASSWORD/TEAM_ID)"
  fi

  if (( ${#notary_creds[@]} )); then
    info "notarytool submit → $(basename "$PKG_OUT") (Apple scan; usually 1–5 min)"
    stdout_out="$(mktemp)"; stderr_out="$(mktemp)"; exit_code=0
    xcrun notarytool submit "$PKG_OUT" "${notary_creds[@]}" --wait \
      >"$stdout_out" 2>"$stderr_out" &
    notary_pid=$!
    SECONDS=0; warned_long=0
    while kill -0 "$notary_pid" 2>/dev/null; do
      sleep 10
      printf '%s   ⏳ notarizing… %dm%02ds elapsed%s\r' \
        "$C_BLUE" "$(( SECONDS / 60 ))" "$(( SECONDS % 60 ))" "$C_RESET"
      if (( SECONDS >= 1200 && warned_long == 0 )); then
        warned_long=1; printf '\n'; warn "20+ min — Apple's queue may be backed up; still waiting…"
      fi
    done
    printf '\n'
    wait "$notary_pid" || exit_code=$?
    if (( exit_code )) || ! grep -q "status: Accepted" "$stdout_out"; then
      cat "$stdout_out" "$stderr_out" >&2
      rm -f "$stdout_out" "$stderr_out"
      die "notarization failed or not Accepted"
    fi
    rm -f "$stdout_out" "$stderr_out"
    ok "notarytool: Accepted"
    run "xcrun stapler staple '$PKG_OUT'"
    ok "stapled"
  fi
else
  info "skipping notarization (pkg unsigned or dry-run)"
fi

# ─── Gatekeeper assertion ────────────────────────────────────────────────────
hdr "Gatekeeper assertion"
if (( SIGN_PKG && ! DRY_RUN )); then
  spctl_out="$(mktemp)"; spctl_code=0
  spctl --assess --type install -v "$PKG_OUT" >"$spctl_out" 2>&1 || spctl_code=$?
  if (( spctl_code )) || ! grep -q "source=Notarized Developer ID" "$spctl_out"; then
    cat "$spctl_out" >&2; rm -f "$spctl_out"
    warn "spctl did not confirm a notarized installer (ok if notarization was skipped)"
  else
    rm -f "$spctl_out"; ok "spctl: accepted, source=Notarized Developer ID"
  fi
else
  info "skipping spctl assertion (unsigned or dry-run)"
fi

printf '\n%sDone.%s  Distribute: squirrel-installer-macos.pkg\n' "$C_BOLD" "$C_RESET"
printf '       Size: %s\n\n' "$(du -sh "$PKG_OUT" 2>/dev/null | cut -f1 || echo 'n/a')"
