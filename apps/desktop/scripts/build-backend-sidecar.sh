#!/usr/bin/env bash
#
# apps/desktop/scripts/build-backend-sidecar.sh
#
# PyInstaller-builds the Python backend and places the resulting binary at
# apps/desktop/src-tauri/bin/squirrel-backend-${TARGET_TRIPLE} so Tauri's
# `bundle.externalBin` picks it up and ships it inside the .app.
#
# Wired into tauri.conf.json via `beforeBundleCommand`, so it runs
# automatically as part of `pnpm tauri build`. Can also be invoked
# standalone (`pnpm tauri:prebuild-backend`) for ad-hoc rebuilds.
#
# Idempotent — re-running rebuilds the binary from scratch. Cheap dev
# experience: skip this script entirely in `tauri dev` (the supervisor
# adopts whatever `make backend-start` produced).
#
# Prerequisites:
#   - pyinstaller on PATH (`pip install pyinstaller`)
#   - pnpm on PATH (to build the backend's browser SPA bundle)
#   - rustc on PATH (to detect target triple)
#
# Exit codes:
#   0 — binary placed at expected location
#   1 — missing prerequisite, build failed, or copy failed

set -euo pipefail

# Resolve key paths from this script's own location so the script doesn't
# care what cwd you run it from.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_ROOT="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$DESKTOP_ROOT/../.." && pwd)"

BACKEND_PY="$REPO_ROOT/apps/backend/server.py"
BACKEND_SPA_DIST="$REPO_ROOT/apps/backend/app/dist"
CLI_LIB="$REPO_ROOT/apps/cli/lib"
PYINSTALLER_DIST="$REPO_ROOT/dist"
PYINSTALLER_BUILD="$REPO_ROOT/build/pyinstaller/backend-tauri"
BIN_OUT_DIR="$DESKTOP_ROOT/src-tauri/bin"

if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_BLUE=$'\033[34m'; C_RED=$'\033[31m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_BLUE=''; C_RED=''; C_RESET=''
fi
say()  { printf '%s\n' "$*"; }
info() { printf '%s   %s%s\n' "$C_BLUE" "$*" "$C_RESET"; }
ok()   { printf '%s✓  %s%s\n' "$C_GREEN" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED" "$*" "$C_RESET" >&2; exit 1; }

# ─── Prerequisites ───────────────────────────────────────────────────────────

command -v pyinstaller >/dev/null 2>&1 \
  || die "pyinstaller not found — run: pip install pyinstaller"
command -v pnpm >/dev/null 2>&1 \
  || die "pnpm not found — see https://pnpm.io"
command -v rustc >/dev/null 2>&1 \
  || die "rustc not found — install Rust (https://rustup.rs)"

[[ -f "$BACKEND_PY" ]] \
  || die "backend entry point missing: $BACKEND_PY"

# ─── Target triple ───────────────────────────────────────────────────────────
# Tauri's bundle.externalBin requires the sidecar binary to be named
# `<base>-<target-triple>` so cross-target builds don't clobber each other.

TARGET_TRIPLE="$(rustc -Vv | awk '/^host:/ {print $2}')"
[[ -n "$TARGET_TRIPLE" ]] \
  || die "could not detect target triple from rustc -Vv"
info "target triple: $TARGET_TRIPLE"

# ─── Backend browser SPA (embedded into the binary) ──────────────────────────
# PyInstaller's --add-data ships apps/backend/app/dist/ inside the binary
# so the running backend can serve the SPA at /. If the SPA is missing we
# build it; if it's present we trust it (callers can pre-build for speed).

if [[ ! -d "$BACKEND_SPA_DIST" ]]; then
  info "browser SPA dist missing; building squirrel-web-ui..."
  (cd "$REPO_ROOT" && pnpm -F squirrel-web-ui build) \
    || die "backend SPA build failed"
fi
[[ -d "$BACKEND_SPA_DIST" ]] \
  || die "backend SPA dist still missing after build: $BACKEND_SPA_DIST"
ok "backend SPA present at apps/backend/app/dist/"

# ─── PyInstaller ─────────────────────────────────────────────────────────────

mkdir -p "$PYINSTALLER_DIST" "$PYINSTALLER_BUILD"

info "running pyinstaller..."
# Silence the `pkg_resources is deprecated as an API` UserWarning. It originates
# in PyInstaller's own dependency (altgraph importing pkg_resources), not in our
# code, and isn't actionable here. The filter is scoped to this invocation and
# matched by message+category so it can't mask warnings from server.py itself.
PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" \
pyinstaller \
  --onefile \
  --name squirrel-backend \
  --distpath "$PYINSTALLER_DIST" \
  --workpath "$PYINSTALLER_BUILD" \
  --specpath "$PYINSTALLER_BUILD" \
  --paths "$CLI_LIB" \
  --add-data "$BACKEND_SPA_DIST:app/dist" \
  --clean \
  --noconfirm \
  "$BACKEND_PY" >/dev/null

BUILT_BIN="$PYINSTALLER_DIST/squirrel-backend"
[[ -f "$BUILT_BIN" ]] \
  || die "pyinstaller did not produce expected binary at $BUILT_BIN"
ok "pyinstaller produced $BUILT_BIN ($(du -h "$BUILT_BIN" | cut -f1))"

# ─── Place at the Tauri-expected path ────────────────────────────────────────

mkdir -p "$BIN_OUT_DIR"
OUT_BIN="$BIN_OUT_DIR/squirrel-backend-$TARGET_TRIPLE"
cp -f "$BUILT_BIN" "$OUT_BIN"
chmod +x "$OUT_BIN"
ok "sidecar placed at apps/desktop/src-tauri/bin/squirrel-backend-$TARGET_TRIPLE"

say ""
ok "backend sidecar ready for tauri bundle"
