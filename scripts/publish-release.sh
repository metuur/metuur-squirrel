#!/usr/bin/env bash
# scripts/publish-release.sh — Publish the macOS installer DMG as a GitHub Release.
#
# Companion to scripts/build-dmg.sh. Reads the version from dmg-staging/VERSION
# (which build-dmg.sh writes from apps/cli/pyproject.toml), tags the current
# commit as vX.Y.Z, pushes the tag, and creates/updates a GitHub Release on
# the target repo (default: metuur/metuur-squirrel).
#
# Usage:
#   ./scripts/publish-release.sh                              # build (if missing) + tag + release
#   ./scripts/publish-release.sh --rebuild                    # always rebuild the DMG first
#   ./scripts/publish-release.sh --no-build                   # require existing DMG, skip build
#   ./scripts/publish-release.sh --dmg /path/file.dmg         # use a specific DMG file
#   ./scripts/publish-release.sh --repo owner/name            # target a different repo (e.g. squirrel-releases)
#   ./scripts/publish-release.sh --clobber                    # re-upload DMG to an existing release
#   ./scripts/publish-release.sh --draft                      # create as draft (not public)
#   ./scripts/publish-release.sh --prerelease                 # mark as pre-release
#   ./scripts/publish-release.sh --notes "text"               # custom release notes
#   ./scripts/publish-release.sh --dry-run                    # print steps without executing
#
# Prerequisites:
#   gh   (brew install gh && gh auth login   — needs 'repo' scope)
#   git  (clean tree recommended; the script warns if dirty)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="metuur/metuur-squirrel"
DMG="$ROOT/squirrel-installer-macos.dmg"
VERSION_FILE="$ROOT/dmg-staging/VERSION"

REBUILD=0
NO_BUILD=0
CLOBBER=0
DRAFT=0
PRERELEASE=0
DRY_RUN=0
CUSTOM_NOTES=""
CUSTOM_DMG=""

while (( $# )); do
  case "$1" in
    --rebuild)     REBUILD=1 ;;
    --no-build)    NO_BUILD=1 ;;
    --clobber)     CLOBBER=1 ;;
    --draft)       DRAFT=1 ;;
    --prerelease)  PRERELEASE=1 ;;
    --dry-run)     DRY_RUN=1 ;;
    --notes)       shift; CUSTOM_NOTES="${1:-}" ;;
    --dmg)         shift; CUSTOM_DMG="${1:-}" ;;
    --repo)        shift; REPO="${1:-}"; [[ -n "$REPO" ]] || die "--repo requires owner/name" ;;
    -h|--help)     sed -n '2,22p' "$0"; exit 0 ;;
    *)             printf 'Unknown arg: %s\n' "$1" >&2; exit 1 ;;
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
say()  { printf '%s\n' "$*"; }
ok()   { printf '%s✓  %s%s\n' "$C_GREEN"  "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE"   "$*" "$C_RESET"; }
warn() { printf '%s⚠  %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
hdr()  { printf '\n%s=== %s ===%s\n' "$C_BOLD" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED" "$*" "$C_RESET" >&2; exit 1; }
run()  { info "$*"; (( DRY_RUN )) || eval "$*"; }

# ─── Preflight ───────────────────────────────────────────────────────────────
hdr "Preflight"
command -v gh  >/dev/null 2>&1 || die "gh not found — brew install gh"
command -v git >/dev/null 2>&1 || die "git not found"
gh auth status >/dev/null 2>&1 || die "gh not authenticated — run: gh auth login"
ok "gh authenticated"

# Clean tree check (warn only — DMG content is what matters, not the worktree)
if ! git -C "$ROOT" diff --quiet || ! git -C "$ROOT" diff --cached --quiet; then
  warn "working tree is dirty — the tag will point at the last committed state"
fi

# ─── Step 1: Build (or reuse) the DMG ────────────────────────────────────────
hdr "Step 1 — Installer DMG"
if [[ -n "$CUSTOM_DMG" ]]; then
  (( REBUILD ))  && die "--dmg and --rebuild are mutually exclusive"
  (( NO_BUILD )) && die "--dmg and --no-build are mutually exclusive"
  DMG="$(cd "$(dirname "$CUSTOM_DMG")" && pwd)/$(basename "$CUSTOM_DMG")"
  (( DRY_RUN )) || [[ -f "$DMG" ]] || die "DMG not found at $DMG"
  ok "using provided DMG: $DMG ($(du -sh "$DMG" 2>/dev/null | cut -f1))"
elif (( REBUILD )); then
  (( NO_BUILD )) && die "--rebuild and --no-build are mutually exclusive"
  run "bash '$ROOT/scripts/build-dmg.sh'"
elif [[ ! -f "$DMG" ]]; then
  (( NO_BUILD )) && die "DMG missing at $DMG and --no-build was passed"
  info "DMG missing — building"
  run "bash '$ROOT/scripts/build-dmg.sh'"
else
  ok "reusing existing $DMG ($(du -sh "$DMG" 2>/dev/null | cut -f1))"
fi
if (( ! DRY_RUN )); then
  [[ -f "$DMG" ]] || die "DMG not found at $DMG"
  [[ -f "$VERSION_FILE" ]] || die "VERSION file missing at $VERSION_FILE — re-run with --rebuild"
fi

# ─── Step 2: Version + tag ───────────────────────────────────────────────────
hdr "Step 2 — Tag"
VERSION="$( (( DRY_RUN )) && echo "DRYRUN" || cat "$VERSION_FILE")"
TAG="v$VERSION"
say "Version: $VERSION   Tag: $TAG   Repo: $REPO"

# Skip git tag/push when targeting an external repo (e.g. squirrel-releases)
# — that repo has no local working tree to tag.
SOURCE_REPO="metuur/metuur-squirrel"
if [[ "$REPO" == "$SOURCE_REPO" ]]; then
  if (( ! DRY_RUN )) && git -C "$ROOT" rev-parse "$TAG" >/dev/null 2>&1; then
    warn "tag $TAG already exists locally — skipping tag creation"
  else
    run "git -C '$ROOT' tag -a '$TAG' -m 'Squirrel $TAG'"
  fi

  if (( ! DRY_RUN )) && git -C "$ROOT" ls-remote --tags origin "refs/tags/$TAG" | grep -q "$TAG"; then
    warn "tag $TAG already on origin — skipping push"
  else
    run "git -C '$ROOT' push origin '$TAG'"
  fi
else
  info "external releases repo — skipping git tag (no local tree to tag)"
fi

# ─── Step 3: Release ─────────────────────────────────────────────────────────
hdr "Step 3 — GitHub Release"

DMG_SIZE="$( (( DRY_RUN )) && echo "n/a" || du -sh "$DMG" | cut -f1)"
if [[ -n "$CUSTOM_NOTES" ]]; then
  NOTES="$CUSTOM_NOTES"
else
  NOTES="macOS installer bundle (CLI + backend + agent-pack).

**Install**
\`\`\`bash
hdiutil attach squirrel-installer-macos.dmg
\"/Volumes/Squirrel $VERSION/Install Squirrel\"
\`\`\`

Size: $DMG_SIZE"
fi

FLAGS=""
(( DRAFT ))      && FLAGS+=" --draft"
(( PRERELEASE )) && FLAGS+=" --prerelease"

# Does the release already exist?
RELEASE_EXISTS=0
if (( ! DRY_RUN )) && gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  RELEASE_EXISTS=1
fi

if (( RELEASE_EXISTS )); then
  if (( CLOBBER )); then
    warn "release $TAG already exists — re-uploading DMG (--clobber)"
    run "gh release upload '$TAG' '$DMG' --repo '$REPO' --clobber"
  else
    die "release $TAG already exists. Re-run with --clobber to replace the DMG, or bump apps/cli/pyproject.toml version."
  fi
else
  NOTES_FILE="$(mktemp -t squirrel-release-notes.XXXXXX)"
  trap 'rm -f "$NOTES_FILE"' EXIT
  printf '%s\n' "$NOTES" > "$NOTES_FILE"
  run "gh release create '$TAG' '$DMG' \
    --repo '$REPO' \
    --title 'Squirrel $TAG' \
    --notes-file '$NOTES_FILE'$FLAGS"
fi

# ─── Done ────────────────────────────────────────────────────────────────────
hdr "Done"
if (( ! DRY_RUN )); then
  URL="$(gh release view "$TAG" --repo "$REPO" --json url --jq .url 2>/dev/null || true)"
  ok "Published: ${URL:-https://github.com/$REPO/releases/tag/$TAG}"
  say "Direct download:"
  say "  https://github.com/$REPO/releases/download/$TAG/squirrel-installer-macos.dmg"
else
  ok "Dry run complete — no changes made."
fi
say ""
