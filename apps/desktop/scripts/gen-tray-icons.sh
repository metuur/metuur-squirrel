#!/usr/bin/env bash
# Generate the four tray-icon state variants from the white-silhouette source.
#
# Output:
#   src-tauri/icons/tray/{normal,notification,processing,error}.png      (16x16)
#   src-tauri/icons/tray/{normal,notification,processing,error}@2x.png   (32x32)
#
# Variants are distinguished by SHAPE (badge overlay), not colour, so the PNGs
# work as macOS template images — macOS tints them automatically per appearance.
#
# Layout: silhouette anchored bottom-left (south-west gravity) so the top-right
# corner is reserved for the state badge.
#
# Requires: ImageMagick (`magick`).

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HERE/.." && pwd)"
# Source: white-on-transparent line-art derived from squirrel-brand.png.
# (squirrel-bar-white.png from the user's design folder turned out to be a
# nearly-empty test export, so we re-derive the silhouette from the brand mark.)
SRC="$REPO_ROOT/src-tauri/icons/source/squirrel-silhouette.png"
DEST="$REPO_ROOT/src-tauri/icons/tray"

if ! command -v magick >/dev/null 2>&1; then
  echo "magick (ImageMagick) not found on PATH" >&2
  exit 1
fi

if [[ ! -f "$SRC" ]]; then
  echo "source image missing: $SRC" >&2
  exit 1
fi

mkdir -p "$DEST"

# Build the base 32x32 silhouette.
#   1. -trim to remove transparent padding (source has the squirrel at 21x23
#      inside a 39x36 frame)
#   2. resize trimmed silhouette into a 24x24 box
#   3. compose onto 32x32 canvas anchored south-west so the top-right ~8x8
#      area is reserved for the state badge
magick "$SRC" \
  -background none -alpha on \
  -trim +repage \
  -resize 30x30 \
  -gravity southwest -extent 32x32 \
  "$DEST/normal@2x.png"

# Notification: solid disc badge at (~26, 5), radius ~3.
magick "$DEST/normal@2x.png" \
  -fill white -stroke none \
  -draw "circle 26,5 29,5" \
  "$DEST/notification@2x.png"

# Processing: hollow ring badge.
magick "$DEST/normal@2x.png" \
  -fill none -stroke white -strokewidth 1.4 \
  -draw "circle 26,5 29,5" \
  "$DEST/processing@2x.png"

# Error: small X mark.
magick "$DEST/normal@2x.png" \
  -stroke white -strokewidth 1.6 -fill none \
  -draw "line 23,2 29,8" \
  -draw "line 29,2 23,8" \
  "$DEST/error@2x.png"

# Downscale each @2x to 16x16 for the 1x menu-bar size.
for variant in normal notification processing error; do
  magick "$DEST/${variant}@2x.png" \
    -filter Lanczos \
    -resize 16x16 \
    "$DEST/${variant}.png"
done

echo "Generated $(ls "$DEST"/*.png | wc -l | tr -d ' ') tray-icon PNGs in $DEST"
ls -la "$DEST"/*.png
