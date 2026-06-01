#!/usr/bin/env bash
# scripts/publish.sh — Full Squirrel release: GHCR package + public GitHub Release.
#
# What it does:
#   1. Pushes squirrel-installer-macos.dmg to GHCR as an OCI artifact
#      → visible at https://github.com/orgs/metuur/packages/container/squirrel-installer
#   2. Creates a GitHub Release on metuur/squirrel-releases (public repo)
#      → gives users a clean, unauthenticated download URL
#
# The source repo (metuur/metuur-squirrel) stays private throughout.
#
# Usage:
#   ./scripts/publish.sh                         # build (if missing) + publish both
#   ./scripts/publish.sh --rebuild               # force rebuild DMG first
#   ./scripts/publish.sh --no-build              # require existing DMG, skip build
#   ./scripts/publish.sh --dmg /path/file.dmg    # use a specific DMG file
#   ./scripts/publish.sh --clobber               # replace assets in an existing release
#   ./scripts/publish.sh --draft                 # create release as draft
#   ./scripts/publish.sh --prerelease            # mark release as pre-release
#   ./scripts/publish.sh --dry-run               # print steps without executing
#   ./scripts/publish.sh --ghcr-only             # skip the GitHub Release step
#   ./scripts/publish.sh --release-only          # skip the GHCR step
#
# One-time setup:
#   1. Create https://github.com/new → name: squirrel-releases, owner: metuur,
#      Visibility: Public, no README/gitignore. That's all.
#   2. brew install oras
#   3. gh auth refresh -s write:packages

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS="$ROOT/scripts"

# ─── Defaults ────────────────────────────────────────────────────────────────
REBUILD=0; NO_BUILD=0; CLOBBER=0; DRAFT=0; PRERELEASE=0; DRY_RUN=0
GHCR_ONLY=0; RELEASE_ONLY=0
CUSTOM_DMG=""

while (( $# )); do
  case "$1" in
    --rebuild)       REBUILD=1 ;;
    --no-build)      NO_BUILD=1 ;;
    --dmg)           shift; CUSTOM_DMG="${1:-}" ;;
    --clobber)       CLOBBER=1 ;;
    --draft)         DRAFT=1 ;;
    --prerelease)    PRERELEASE=1 ;;
    --dry-run)       DRY_RUN=1 ;;
    --ghcr-only)     GHCR_ONLY=1 ;;
    --release-only)  RELEASE_ONLY=1 ;;
    -h|--help)       sed -n '2,28p' "$0"; exit 0 ;;
    *)               printf 'Unknown arg: %s\n' "$1" >&2; exit 1 ;;
  esac
  shift
done

(( GHCR_ONLY && RELEASE_ONLY )) && { printf '✗  --ghcr-only and --release-only are mutually exclusive\n' >&2; exit 1; }

# ─── Colors ──────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'
  C_RED=$'\033[31m';   C_YELLOW=$'\033[33m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_BLUE=''; C_BOLD=''; C_RED=''; C_YELLOW=''; C_RESET=''
fi
ok()   { printf '%s✓  %s%s\n' "$C_GREEN"  "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE"   "$*" "$C_RESET"; }
hdr()  { printf '\n%s=== %s ===%s\n' "$C_BOLD" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED" "$*" "$C_RESET" >&2; exit 1; }

# ─── Build shared args for sub-scripts ───────────────────────────────────────
SHARED_ARGS=()
(( REBUILD ))   && SHARED_ARGS+=(--rebuild)
(( NO_BUILD ))  && SHARED_ARGS+=(--no-build)
(( DRY_RUN ))   && SHARED_ARGS+=(--dry-run)
[[ -n "$CUSTOM_DMG" ]] && SHARED_ARGS+=(--dmg "$CUSTOM_DMG")

RELEASE_ARGS=("${SHARED_ARGS[@]}")
(( CLOBBER ))    && RELEASE_ARGS+=(--clobber)
(( DRAFT ))      && RELEASE_ARGS+=(--draft)
(( PRERELEASE )) && RELEASE_ARGS+=(--prerelease)

# ─── Step 1: GHCR ────────────────────────────────────────────────────────────
if (( ! RELEASE_ONLY )); then
  hdr "Part 1 — GHCR (org packages page)"
  bash "$SCRIPTS/publish-ghcr.sh" "${SHARED_ARGS[@]}"
  # After the first run, the DMG is already built — tell the release step to skip rebuild
  if (( ! NO_BUILD )) && [[ -z "$CUSTOM_DMG" ]]; then
    RELEASE_ARGS+=(--no-build)
  fi
fi

# ─── Step 2: GitHub Release on the public releases repo ──────────────────────
if (( ! GHCR_ONLY )); then
  hdr "Part 2 — GitHub Release (public download URL)"
  bash "$SCRIPTS/publish-release.sh" --repo metuur/squirrel-releases "${RELEASE_ARGS[@]}"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
hdr "All done"
VERSION_FILE="$ROOT/dmg-staging/VERSION"
VERSION="$( (( DRY_RUN )) && echo "DRYRUN" || cat "$VERSION_FILE" 2>/dev/null || echo "?")"
ok "GHCR package:   https://github.com/orgs/metuur/packages/container/squirrel-installer"
ok "Download URL:   https://github.com/metuur/squirrel-releases/releases/download/v${VERSION}/squirrel-installer-macos.dmg"
printf '\n'
