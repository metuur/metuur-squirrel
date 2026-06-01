#!/usr/bin/env bash
# scripts/publish-npm.sh — Publish the macOS installer as @metuur/squirrel-installer
# on GitHub Packages (npm registry).
#
# Appears at: https://github.com/orgs/metuur/packages?repo_name=metuur-squirrel
# Install:    npm install @metuur/squirrel-installer --registry https://npm.pkg.github.com
#
# Usage:
#   ./scripts/publish-npm.sh                         # build (if missing) + publish
#   ./scripts/publish-npm.sh --rebuild               # force rebuild DMG first
#   ./scripts/publish-npm.sh --no-build              # require existing DMG, skip build
#   ./scripts/publish-npm.sh --dmg /path/file.dmg    # use a specific DMG file
#   ./scripts/publish-npm.sh --dry-run               # print steps without executing
#
# Prerequisites:
#   node + npm  (brew install node)
#   gh auth login  (token needs write:packages scope)
#   gh auth refresh -s write:packages   (if not already granted)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DMG="$ROOT/squirrel-installer-macos.dmg"
VERSION_FILE="$ROOT/dmg-staging/VERSION"

REBUILD=0; NO_BUILD=0; DRY_RUN=0
CUSTOM_DMG=""

while (( $# )); do
  case "$1" in
    --rebuild)  REBUILD=1 ;;
    --no-build) NO_BUILD=1 ;;
    --dry-run)  DRY_RUN=1 ;;
    --dmg)      shift; CUSTOM_DMG="${1:-}" ;;
    -h|--help)  sed -n '2,18p' "$0"; exit 0 ;;
    *)          printf 'Unknown arg: %s\n' "$1" >&2; exit 1 ;;
  esac
  shift
done

# ─── Colors ──────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'
  C_RED=$'\033[31m';   C_YELLOW=$'\033[33m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_BLUE=''; C_BOLD=''; C_RED=''; C_YELLOW=''; C_RESET=''
fi
ok()   { printf '%s✓  %s%s\n' "$C_GREEN"  "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE"   "$*" "$C_RESET"; }
warn() { printf '%s⚠  %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
hdr()  { printf '\n%s=== %s ===%s\n' "$C_BOLD" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED" "$*" "$C_RESET" >&2; exit 1; }
run()  { info "$*"; (( DRY_RUN )) || eval "$*"; }

# ─── Preflight ───────────────────────────────────────────────────────────────
hdr "Preflight"
command -v npm >/dev/null 2>&1 || die "npm not found — brew install node"
command -v gh  >/dev/null 2>&1 || die "gh not found — brew install gh"
gh auth status >/dev/null 2>&1 || die "gh not authenticated — run: gh auth login"
ok "npm $(npm --version), gh available"

# ─── Step 1: DMG ─────────────────────────────────────────────────────────────
hdr "Step 1 — Installer DMG"
if [[ -n "$CUSTOM_DMG" ]]; then
  (( REBUILD ))  && die "--dmg and --rebuild are mutually exclusive"
  (( NO_BUILD )) && die "--dmg and --no-build are mutually exclusive"
  DMG="$(cd "$(dirname "$CUSTOM_DMG")" && pwd)/$(basename "$CUSTOM_DMG")"
  (( DRY_RUN )) || [[ -f "$DMG" ]] || die "DMG not found at $DMG"
  ok "using $DMG ($(du -sh "$DMG" 2>/dev/null | cut -f1))"
  if [[ ! -f "$VERSION_FILE" ]]; then
    VERSION="$(basename "$DMG" .dmg | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)"
    [[ -n "$VERSION" ]] || die "Cannot infer version — no dmg-staging/VERSION and no semver in filename"
    warn "inferred version $VERSION from filename"
  fi
elif (( REBUILD )); then
  run "bash '$ROOT/scripts/build-dmg.sh'"
elif [[ ! -f "$DMG" ]]; then
  (( NO_BUILD )) && die "DMG missing and --no-build was set"
  info "DMG missing — building"; run "bash '$ROOT/scripts/build-dmg.sh'"
else
  ok "reusing $DMG ($(du -sh "$DMG" 2>/dev/null | cut -f1))"
fi
(( DRY_RUN )) || { [[ -f "$DMG" ]] || die "DMG not found"; }

VERSION="${VERSION:-$( (( DRY_RUN )) && echo "0.0.0-dryrun" || cat "$VERSION_FILE")}"
ZIP_NAME="squirrel-installer-macos.zip"

# ─── Step 2: Zip DMG ─────────────────────────────────────────────────────────
hdr "Step 2 — Compress DMG → zip"
WORK_DIR="$(mktemp -d -t squirrel-npm-pkg.XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT

run "( cd '$(dirname "$DMG")' && zip -q '$WORK_DIR/$ZIP_NAME' '$(basename "$DMG")' )"
if (( ! DRY_RUN )); then
  ok "$ZIP_NAME  ($(du -sh "$WORK_DIR/$ZIP_NAME" | cut -f1))"
fi

# ─── Step 3: Write package.json ──────────────────────────────────────────────
hdr "Step 3 — package.json"
if (( ! DRY_RUN )); then
  cat > "$WORK_DIR/package.json" <<EOF
{
  "name": "@metuur/squirrel-installer",
  "version": "$VERSION",
  "description": "Squirrel macOS installer bundle (CLI + backend + agent-pack)",
  "files": ["$ZIP_NAME"],
  "os": ["darwin"],
  "publishConfig": {
    "registry": "https://npm.pkg.github.com",
    "access": "public"
  },
  "repository": {
    "type": "git",
    "url": "https://github.com/metuur/metuur-squirrel"
  }
}
EOF
  ok "package.json written (version $VERSION)"
else
  info "would write package.json for @metuur/squirrel-installer@$VERSION"
fi

# ─── Step 4: Auth .npmrc ─────────────────────────────────────────────────────
hdr "Step 4 — npm auth"
if (( ! DRY_RUN )); then
  NPM_TOKEN="$(gh auth token)"
  cat > "$WORK_DIR/.npmrc" <<EOF
//npm.pkg.github.com/:_authToken=${NPM_TOKEN}
@metuur:registry=https://npm.pkg.github.com
EOF
  ok "wrote .npmrc with gh token"
else
  info "would write .npmrc with token from gh auth"
fi

# ─── Step 5: Publish ─────────────────────────────────────────────────────────
hdr "Step 5 — npm publish"
run "( cd '$WORK_DIR' && npm publish )"

# ─── Done ────────────────────────────────────────────────────────────────────
hdr "Done"
ok "Published: @metuur/squirrel-installer@$VERSION"
printf '\n'
printf '%sPackages page:%s\n'  "$C_BOLD" "$C_RESET"
printf '  https://github.com/orgs/metuur/packages?repo_name=metuur-squirrel\n'
printf '\n'
printf '%sInstall:%s\n' "$C_BOLD" "$C_RESET"
printf '  npm install @metuur/squirrel-installer --registry https://npm.pkg.github.com\n'
printf '\n'
