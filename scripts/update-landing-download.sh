#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/landing/pages/downloads.json"
DEFAULT_PREFIX="https://squirrel-file.metuur.com/dmg/squirrel-macos-v"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/update-landing-download.sh 0.7.29
  ./scripts/update-landing-download.sh v0.7.29
  ./scripts/update-landing-download.sh --url https://squirrel-file.metuur.com/dmg/squirrel-macos-v0.7.29.dmg
  ./scripts/update-landing-download.sh 0.7.29 --deploy

Updates landing/pages/downloads.json so the landing page points all download
buttons at the current macOS installer.
EOF
}

VERSION=""
URL=""
DEPLOY=0

while (( $# )); do
  case "$1" in
    --url)
      shift
      URL="${1:-}"
      ;;
    --deploy)
      DEPLOY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      VERSION="$1"
      ;;
  esac
  shift || true
done

if [[ -z "$VERSION" && -z "$URL" ]]; then
  usage >&2
  exit 1
fi

if [[ -n "$VERSION" ]]; then
  VERSION="${VERSION#v}"
  URL="${DEFAULT_PREFIX}${VERSION}.dmg"
fi

if [[ -z "$URL" ]]; then
  echo "Missing URL" >&2
  exit 1
fi

if [[ "$URL" =~ squirrel-macos-v([^/]+)\.dmg$ ]]; then
  VERSION="${BASH_REMATCH[1]}"
fi

if [[ -z "$VERSION" ]]; then
  echo "Could not infer version from URL: $URL" >&2
  exit 1
fi

cat > "$MANIFEST" <<EOF
{
  "macos": {
    "version": "$VERSION",
    "url": "$URL"
  }
}
EOF

printf 'Updated %s\n' "$MANIFEST"
printf 'macOS version: %s\n' "$VERSION"
printf 'macOS URL: %s\n' "$URL"

if (( DEPLOY )); then
  cd "$ROOT"
  wrangler pages deploy landing/pages
fi
