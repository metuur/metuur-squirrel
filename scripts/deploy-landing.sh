#!/usr/bin/env bash
# scripts/deploy-landing.sh — Deploy the Squirrel landing page to Cloudflare Pages
# and upload the macOS .dmg to the Cloudflare R2 bucket.
#
# What it does:
#   1. Uploads the macOS installer .dmg to the R2 bucket "squirrel" at
#      dmg/squirrel-macos-v<version>.dmg (served at squirrel-file.metuur.com).
#   2. Updates landing/pages/downloads.json to point at that version/URL.
#   3. Deploys landing/pages to Cloudflare Pages via `wrangler pages deploy`.
#
# Version is read from package.json. The .dmg is auto-located unless --dmg is given.
#
# Usage:
#   ./scripts/deploy-landing.sh                 # upload dmg + update manifest + deploy pages
#   ./scripts/deploy-landing.sh --pages-only    # only deploy the landing page
#   ./scripts/deploy-landing.sh --dmg-only      # only upload the dmg + update manifest
#   ./scripts/deploy-landing.sh --dmg /path.dmg # use a specific .dmg file
#   ./scripts/deploy-landing.sh --version 0.8.0 # override the version
#   ./scripts/deploy-landing.sh --branch <name> # Pages branch (default: production branch)
#   ./scripts/deploy-landing.sh --preview       # deploy as a Preview (current git branch)
#   ./scripts/deploy-landing.sh --dry-run       # print actions without running them
#
# Cloudflare Pages treats a deploy as Production only when its branch matches the
# project's production branch. This script deploys to PROD_BRANCH by default.
#
# Requires: wrangler (logged in: `wrangler login`), jq.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAGES_DIR="$ROOT/landing/pages"
R2_BUCKET="squirrel"
R2_PREFIX="dmg"
PUBLIC_BASE="https://squirrel-file.metuur.com/dmg"
PROD_BRANCH="squirrel"   # the Pages project's production branch

VERSION=""
DMG=""
PAGES_BRANCH=""
PREVIEW=0
DO_PAGES=1
DO_DMG=1
DRY_RUN=0

usage() { sed -n '2,28p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

run() {
  if (( DRY_RUN )); then
    printf '[dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

while (( $# )); do
  case "$1" in
    --pages-only) DO_DMG=0 ;;
    --dmg-only)   DO_PAGES=0 ;;
    --dmg)        shift; DMG="${1:-}" ;;
    --version)    shift; VERSION="${1:-}" ;;
    --branch)     shift; PAGES_BRANCH="${1:-}" ;;
    --preview)    PREVIEW=1 ;;
    --dry-run)    DRY_RUN=1 ;;
    -h|--help)    usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
  shift || true
done

command -v wrangler >/dev/null 2>&1 || { echo "wrangler not found on PATH" >&2; exit 1; }

if [[ -z "$VERSION" ]]; then
  command -v jq >/dev/null 2>&1 || { echo "jq not found (needed to read version)" >&2; exit 1; }
  VERSION="$(jq -r '.version' "$ROOT/package.json")"
fi
VERSION="${VERSION#v}"
[[ -n "$VERSION" ]] || { echo "Could not determine version" >&2; exit 1; }

cd "$ROOT"

# --- 1 & 2: upload dmg to R2 + update manifest ------------------------------
if (( DO_DMG )); then
  if [[ -z "$DMG" ]]; then
    for cand in \
      "$ROOT/squirrel-macos-v${VERSION}-arm64.dmg" \
      "$ROOT/squirrel-macos-arm64.dmg" \
      "$ROOT/squirrel-macos.dmg" \
      "$ROOT/target/aarch64-apple-darwin/release/bundle/dmg/Squirrel_${VERSION}_aarch64.dmg" \
      "$ROOT/target/release/bundle/dmg/Squirrel_${VERSION}_aarch64.dmg"; do
      if [[ -f "$cand" ]]; then DMG="$cand"; break; fi
    done
  fi
  [[ -n "$DMG" && -f "$DMG" ]] || { echo "No .dmg found for version $VERSION (pass --dmg <path>)" >&2; exit 1; }

  KEY="${R2_PREFIX}/squirrel-macos-v${VERSION}.dmg"

  echo "Uploading $DMG"
  echo "  -> r2://${R2_BUCKET}/${KEY}"
  run wrangler r2 object put "${R2_BUCKET}/${KEY}" \
    --file "$DMG" \
    --content-type application/x-apple-diskimage \
    --remote

  echo "Updating landing manifest via update-landing-download.sh"
  run "$ROOT/scripts/update-landing-download.sh" "$VERSION"
fi

# --- 3: deploy landing page to Cloudflare Pages -----------------------------
if (( DO_PAGES )); then
  # Default to the production branch so the deploy lands in Production, unless
  # --preview was passed (then let wrangler use the current git branch) or an
  # explicit --branch was given.
  if [[ -z "$PAGES_BRANCH" && "$PREVIEW" -eq 0 ]]; then
    PAGES_BRANCH="$PROD_BRANCH"
  fi

  deploy_args=(pages deploy "$PAGES_DIR" --commit-dirty=true)
  if [[ -n "$PAGES_BRANCH" ]]; then
    deploy_args+=(--branch "$PAGES_BRANCH")
    echo "Deploying $PAGES_DIR to Cloudflare Pages (branch: $PAGES_BRANCH)"
  else
    echo "Deploying $PAGES_DIR to Cloudflare Pages (preview: current git branch)"
  fi
  run wrangler "${deploy_args[@]}"
fi

echo "Done."
