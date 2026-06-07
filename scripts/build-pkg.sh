#!/usr/bin/env bash
# scripts/build-pkg.sh — Builds the Squirrel all-in-one macOS .pkg installer.
#
# Produces squirrel-installer-macos.pkg: a guided, double-click installer that
# lays down the desktop app, the CLI binaries, and staged agent-pack, then runs
# a postinstall that configures the logged-in user (config, vault, agent-pack).
# Finally wraps the .pkg into squirrel-macos.dmg so end users can mount it and
# double-click the installer.
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
# The standalone .pkg is an INTERNAL artifact (debug / CI / advanced installs):
# it lives under build/, not the repo root. The single PUBLIC artifact is the
# DMG below, which wraps this .pkg. See `make build-pkg`.
PKG_OUT="$BUILD/squirrel-installer-macos.pkg"
DMG_STAGING="$ROOT/pkg-dmg-staging"  # holds the .pkg for hdiutil to wrap
DMG_OUT="$ROOT/squirrel-macos.dmg"   # final DMG that CONTAINS the .pkg (public)
# Hardened-runtime entitlements — lets the bundled squirrel-backend sidecar
# dlopen its PyInstaller-extracted libpython (else "different Team IDs" crash).
ENTITLEMENTS="$ROOT/apps/desktop/src-tauri/Entitlements.plist"
APP_ID="com.metuur.squirrel"
SKIP_BUILD=0
DRY_RUN=0
ARM64_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=1 ;;
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
ok()   { printf '%s✓  %s%s\n' "$C_GREEN" "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE" "$*" "$C_RESET"; }
warn() { printf '%s⚠  %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
hdr()  { printf '\n%s=== %s ===%s\n' "$C_BOLD" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED" "$*" "$C_RESET" >&2; exit 1; }
run()  { info "$*"; (( DRY_RUN )) || eval "$*"; }

# _notarize_staple <artifact> — submit <artifact> to Apple's notary service,
# wait with an elapsed-time heartbeat, then staple the ticket on Acceptance.
# Reads notary creds from $notary_creds (set by the caller). No-op if empty.
_notarize_staple() {
  local artifact="$1"
  if (( ! ${#notary_creds[@]} )); then return 0; fi
  info "notarytool submit → $(basename "$artifact") (Apple scan; usually 1–5 min)"
  local stdout_out stderr_out exit_code=0
  stdout_out="$(mktemp)"; stderr_out="$(mktemp)"
  xcrun notarytool submit "$artifact" "${notary_creds[@]}" --wait \
    >"$stdout_out" 2>"$stderr_out" &
  local notary_pid=$!
  SECONDS=0; local warned_long=0
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
    die "notarization failed or not Accepted: $(basename "$artifact")"
  fi
  rm -f "$stdout_out" "$stderr_out"
  ok "notarytool: Accepted"
  run "xcrun stapler staple '$artifact'"
  ok "stapled"
}

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
printf '\n%s🐿  Building Squirrel v%s .pkg installer%s%s\n' "$C_BOLD" "$VERSION" \
  "$( (( ARM64_ONLY )) && printf ' (arm64-only)' )" "$C_RESET"
(( DRY_RUN )) && printf '%s    (dry-run — no files written)%s\n' "$C_BOLD" "$C_RESET"

# ─── Preflight ───────────────────────────────────────────────────────────────
hdr "Preflight"
command -v pkgbuild     >/dev/null 2>&1 || die "pkgbuild not found (macOS only)"
command -v productbuild >/dev/null 2>&1 || die "productbuild not found (macOS only)"
ok "pkgbuild, productbuild available"

# ─── Locate / build inputs ───────────────────────────────────────────────────
hdr "Locate inputs (app + CLI binaries)"

# Where Tauri drops the bundled app depends on the build target. An arm64-only
# build (TAURI_TARGET=aarch64-apple-darwin) lands under the target triple;
# the default/universal build lands at target/release.
if (( ARM64_ONLY )); then
  # Cargo only uses a target-triple subdir when cross-compiling. On an Apple
  # Silicon host, --target aarch64-apple-darwin == host, so the bundle lands in
  # the plain target/release/ tree. List both, triple-dir first.
  APP_CANDIDATES=(
    "$ROOT/target/aarch64-apple-darwin/release/bundle/macos/Squirrel.app"
    "$ROOT/target/release/bundle/macos/Squirrel.app"
    "$ROOT/apps/desktop/src-tauri/target/aarch64-apple-darwin/release/bundle/macos/Squirrel.app"
    "$ROOT/apps/desktop/src-tauri/target/release/bundle/macos/Squirrel.app"
  )
  APP_BUILD_CMD="( cd '$ROOT/apps/desktop' && TAURI_TARGET=aarch64-apple-darwin pnpm tauri:build )"
else
  APP_CANDIDATES=(
    "$ROOT/target/release/bundle/macos/Squirrel.app"
    "$ROOT/apps/desktop/src-tauri/target/release/bundle/macos/Squirrel.app"
  )
  APP_BUILD_CMD="( cd '$ROOT/apps/desktop' && pnpm tauri build )"
fi

APP=""
for cand in "${APP_CANDIDATES[@]}"; do
  [[ -d "$cand" ]] && { APP="$cand"; break; }
done

if [[ -z "$APP" ]]; then
  (( SKIP_BUILD )) && die "Squirrel.app not found and --skip-build set. Build it first (make build-pkg)."
  run "$APP_BUILD_CMD"
  for cand in "${APP_CANDIDATES[@]}"; do
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
  # Sign inside-out (the app has no Frameworks/, just two Mach-O in MacOS/).
  # The sidecar MUST be signed first and carry the library-validation
  # entitlement; re-signing it after the bundle would break the bundle seal.
  # --deep is intentionally NOT used: it would re-sign the sidecar without
  # entitlements, reintroducing the dlopen crash.
  for sc in "$APP/Contents/MacOS/"squirrel-backend*; do
    [[ -f "$sc" ]] || continue
    run "codesign --force --options runtime --timestamp --entitlements '$ENTITLEMENTS' --sign '$APPLE_SIGNING_IDENTITY' '$sc'"
  done
  run "codesign --force --options runtime --timestamp --entitlements '$ENTITLEMENTS' --sign '$APPLE_SIGNING_IDENTITY' '$APP'"
  (( DRY_RUN )) || codesign --verify --strict "$APP" || die "app signature verification failed"
  ok "app + sidecar signed + verified"
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
# Stage GUI resources with the version substituted into welcome.html.
run "mkdir -p '$BUILD/resources'"
run "cp '$PKG_SRC/resources/'*.html '$BUILD/resources/'"
(( DRY_RUN )) || sed -i '' "s/__VERSION__/$VERSION/g" "$BUILD/resources/welcome.html"

UNSIGNED="$BUILD/squirrel-unsigned.pkg"
run "productbuild \
  --distribution '$DISTXML' \
  --package-path '$BUILD' \
  --resources '$BUILD/resources' \
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
# Resolve notarization credentials once; reused for both the .pkg and the DMG.
notary_creds=()
if (( SIGN_PKG && ! DRY_RUN )); then
  # Credentials: prefer a keychain profile (keeps the app-specific password out
  # of the process listing). Fall back to APPLE_ID/PASSWORD/TEAM_ID env vars.
  if [[ -n "${APPLE_KEYCHAIN_PROFILE:-}" ]]; then
    notary_creds=(--keychain-profile "$APPLE_KEYCHAIN_PROFILE")
  elif [[ -n "${APPLE_ID:-}" && -n "${APPLE_PASSWORD:-}" && -n "${APPLE_TEAM_ID:-}" ]]; then
    notary_creds=(--apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD")
    warn "--password passed on the command line (visible via 'ps'); set APPLE_KEYCHAIN_PROFILE to avoid this"
  else
    warn "no notarization credentials — signed but NOT notarized (set APPLE_KEYCHAIN_PROFILE or APPLE_ID/PASSWORD/TEAM_ID)"
  fi
  _notarize_staple "$PKG_OUT"
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

# ─── Wrap the .pkg into a DMG ────────────────────────────────────────────────
hdr "Wrap .pkg into DMG"
run "rm -rf '$DMG_STAGING'"
run "mkdir -p '$DMG_STAGING'"
run "cp '$PKG_OUT' '$DMG_STAGING/'"
run "rm -f '$DMG_OUT'"
run "hdiutil create -volname 'Squirrel $VERSION' -srcfolder '$DMG_STAGING' -ov -format UDZO '$DMG_OUT'"
ok "dmg → ${DMG_OUT#$ROOT/}"

# Sign + notarize + staple the DMG (mirrors the .pkg path).
if (( SIGN_APP && ! DRY_RUN )); then
  run "codesign --sign '$APPLE_SIGNING_IDENTITY' '$DMG_OUT'"
  ok "dmg signed"
  _notarize_staple "$DMG_OUT"
else
  info "skipping DMG signing/notarization (unsigned or dry-run)"
fi

printf '\n%sDone.%s  Distribute: squirrel-macos.dmg  (mount → run the .pkg inside)\n' "$C_BOLD" "$C_RESET"
printf '             internal: %s (standalone .pkg, not for public release)\n' "${PKG_OUT#$ROOT/}"
printf '       Size: pkg %s · dmg %s\n\n' \
  "$(du -sh "$PKG_OUT" 2>/dev/null | cut -f1 || echo 'n/a')" \
  "$(du -sh "$DMG_OUT" 2>/dev/null | cut -f1 || echo 'n/a')"
