#!/usr/bin/env bash
# scripts/publish-ghcr.sh — Publish the macOS installer DMG to GitHub Container
# Registry (GHCR) as an OCI artifact.  The package appears at:
#   https://github.com/orgs/metuur/packages/container/squirrel-installer
#
# Usage:
#   ./scripts/publish-ghcr.sh                         # build (if missing) + push
#   ./scripts/publish-ghcr.sh --rebuild               # always rebuild DMG first
#   ./scripts/publish-ghcr.sh --no-build              # require existing DMG, skip build
#   ./scripts/publish-ghcr.sh --dmg /path/to/file.dmg # push a specific DMG file
#   ./scripts/publish-ghcr.sh --dry-run               # print steps without executing
#
# Prerequisites:
#   brew install oras
#   export GHCR_TOKEN=ghp_xxx   (classic PAT with write:packages scope)
#   OR: gh auth token            (if your gh PAT already has write:packages)
#
# First-time setup (one-off):
#   After push, go to https://github.com/orgs/metuur/packages/container/squirrel-installer
#   → Package settings → Change visibility = Public
#   → Connect repository → metuur/metuur-squirrel

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="ghcr.io/metuur/squirrel-installer"
DMG="$ROOT/squirrel-installer-macos.dmg"
VERSION_FILE="$ROOT/dmg-staging/VERSION"

REBUILD=0
NO_BUILD=0
DRY_RUN=0
CUSTOM_DMG=""

while (( $# )); do
  case "$1" in
    --rebuild)   REBUILD=1 ;;
    --no-build)  NO_BUILD=1 ;;
    --dry-run)   DRY_RUN=1 ;;
    --dmg)       shift; CUSTOM_DMG="${1:-}"; [[ -n "$CUSTOM_DMG" ]] || die "--dmg requires a path" ;;
    -h|--help)   sed -n '2,19p' "$0"; exit 0 ;;
    *)           printf 'Unknown arg: %s\n' "$1" >&2; exit 1 ;;
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
command -v oras >/dev/null 2>&1 || die "oras not found — brew install oras"
ok "oras available"

# Resolve token: prefer GHCR_TOKEN env var, fall back to gh auth token
if [[ -z "${GHCR_TOKEN:-}" ]]; then
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    GHCR_TOKEN="$(gh auth token)"
    info "using token from gh auth"
  else
    die "No token found. Set GHCR_TOKEN=ghp_xxx (needs write:packages scope)\n  or: gh auth login && gh auth token"
  fi
fi
ok "token available"

# ─── Step 1: Build (or reuse) the DMG ────────────────────────────────────────
hdr "Step 1 — Installer DMG"
if [[ -n "$CUSTOM_DMG" ]]; then
  # --dmg path: skip build entirely, use the provided file
  (( REBUILD ))  && die "--dmg and --rebuild are mutually exclusive"
  (( NO_BUILD )) && die "--dmg and --no-build are mutually exclusive"
  DMG="$(cd "$(dirname "$CUSTOM_DMG")" && pwd)/$(basename "$CUSTOM_DMG")"
  (( DRY_RUN )) || [[ -f "$DMG" ]] || die "DMG not found at $DMG"
  ok "using provided DMG: $DMG ($(du -sh "$DMG" 2>/dev/null | cut -f1))"
  # Derive version from the DMG filename if VERSION_FILE is absent
  if [[ ! -f "$VERSION_FILE" ]]; then
    DERIVED="$(basename "$DMG" .dmg | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || true)"
    [[ -n "$DERIVED" ]] || die "Cannot infer version — no dmg-staging/VERSION and no version number in filename"
    VERSION="$DERIVED"
    warn "dmg-staging/VERSION not found — inferred version $VERSION from filename"
  fi
elif (( REBUILD )); then
  (( NO_BUILD )) && die "--rebuild and --no-build are mutually exclusive"
  run "bash '$ROOT/scripts/build-dmg.sh'"
elif [[ ! -f "$DMG" ]]; then
  (( NO_BUILD )) && die "DMG missing at $DMG and --no-build was set"
  info "DMG missing — building"
  run "bash '$ROOT/scripts/build-dmg.sh'"
else
  ok "reusing $DMG ($(du -sh "$DMG" 2>/dev/null | cut -f1))"
fi
if (( ! DRY_RUN )); then
  [[ -f "$DMG" ]] || die "DMG not found at $DMG"
  [[ -f "$VERSION_FILE" || -n "${VERSION:-}" ]] || die "VERSION file missing — re-run with --rebuild"
fi

VERSION="${VERSION:-$( (( DRY_RUN )) && echo "DRYRUN" || cat "$VERSION_FILE")}"
TAG="$IMAGE:$VERSION"
LATEST="$IMAGE:latest"

# ─── Step 2: Zip the DMG ─────────────────────────────────────────────────────
hdr "Step 2 — Compress DMG → zip"
DMG_DIR="$(dirname "$DMG")"
DMG_FILE="$(basename "$DMG")"
ZIP_FILE="${DMG_FILE%.dmg}.zip"
ZIP="$DMG_DIR/$ZIP_FILE"

run "( cd '$DMG_DIR' && zip -q '$ZIP_FILE' '$DMG_FILE' )"
if (( ! DRY_RUN )); then
  ok "Compressed: $ZIP ($(du -sh "$ZIP" | cut -f1))"
fi

# ─── Step 3: Login to GHCR ───────────────────────────────────────────────────
hdr "Step 3 — Login"
if (( DRY_RUN )); then
  info "echo \$GHCR_TOKEN | oras login ghcr.io -u <user> --password-stdin"
else
  GH_USER="$(gh api user --jq .login 2>/dev/null || git config user.name || echo "user")"
  printf '%s\n' "$GHCR_TOKEN" | oras login ghcr.io -u "$GH_USER" --password-stdin
  ok "logged in to ghcr.io as $GH_USER"
fi

# ─── Step 4: Push OCI artifact ───────────────────────────────────────────────
hdr "Step 4 — Push $TAG"
run "( cd '$DMG_DIR' && oras push '$TAG' \
  --artifact-type 'application/vnd.metuur.squirrel.installer' \
  '$ZIP_FILE:application/zip' )"

# Also tag as :latest
run "oras tag '$TAG' '$LATEST'"

# ─── Done ────────────────────────────────────────────────────────────────────
hdr "Done"
ok "Published: $TAG"
ok "Tagged:    $LATEST"
printf '\n'
printf '%sPackages page:%s\n' "$C_BOLD" "$C_RESET"
printf '  https://github.com/orgs/metuur/packages/container/squirrel-installer\n'
printf '\n'
printf '%sPull with oras:%s\n' "$C_BOLD" "$C_RESET"
printf '  oras pull %s\n' "$TAG"
printf '\n'
if (( ! DRY_RUN )); then
  printf '%sFirst-time only:%s connect the package to its repo:\n' "$C_YELLOW" "$C_RESET"
  printf '  https://github.com/orgs/metuur/packages/container/squirrel-installer/settings\n'
  printf '  → Change visibility = Public\n'
  printf '  → Connect repository = metuur/metuur-squirrel\n'
fi
