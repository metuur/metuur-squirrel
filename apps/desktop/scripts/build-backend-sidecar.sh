#!/usr/bin/env bash
#
# apps/desktop/scripts/build-backend-sidecar.sh
#
# Produces a universal (arm64 + x86_64) Mach-O backend sidecar placed at
# apps/desktop/src-tauri/bin/squirrel-backend-${TARGET_TRIPLE} so Tauri's
# bundle.externalBin picks it up inside the .app.
#
# Universal build: PyInstaller runs twice — once natively for the host arch,
# once via Rosetta (Apple Silicon) or arch -arm64 (Intel) for the other arch.
# lipo merges the slices. xattr -cr strips extended attributes before lipo.
#
# Prerequisites:
#   - pyinstaller on PATH for both arm64 and x86_64 Python environments
#   - pnpm on PATH
#   - rustc on PATH (to detect host triple)
#   - rustup with x86_64-apple-darwin target installed
#   - Rosetta (on Apple Silicon; required for the x86_64 PyInstaller slice)
#   - lipo (ships with Xcode Command Line Tools)
#
# Exit codes:
#   0 — universal binary placed at expected location
#   1 — missing prerequisite, build failed, or copy failed

set -euo pipefail

# Set SQUIRREL_ARM64_ONLY=1 to skip the x86_64 slice and lipo step.
# Used by build-manual-zip.sh --arm64-only on machines without Rosetta or the
# x86_64-apple-darwin Rust target.
ARM64_ONLY="${SQUIRREL_ARM64_ONLY:-0}"

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
command -v lipo >/dev/null 2>&1 \
  || die "lipo not found — install Xcode Command Line Tools: xcode-select --install"

[[ -f "$BACKEND_PY" ]] \
  || die "backend entry point missing: $BACKEND_PY"

# ─── Universal binary prerequisites (R-1.6, R-1.7) ───────────────────────────

HOST_ARCH="$(uname -m)"  # arm64 on Apple Silicon, x86_64 on Intel

if (( ARM64_ONLY )); then
  info "arm64-only mode (SQUIRREL_ARM64_ONLY=1) — skipping x86_64 slice and lipo"
else
  # R-1.6: Rust x86_64-apple-darwin target must be installed for universal Tauri build
  if ! rustup target list --installed 2>/dev/null | grep -q "x86_64-apple-darwin"; then
    die "error: x86_64-apple-darwin Rust target not installed — run 'rustup target add x86_64-apple-darwin'"
  fi

  # R-1.7: Rosetta required on Apple Silicon for the x86_64 PyInstaller slice
  if [[ "$HOST_ARCH" == "arm64" ]]; then
    if ! arch -x86_64 /usr/bin/true 2>/dev/null; then
      die "Rosetta is not available — run 'softwareupdate --install-rosetta' and then re-run this script"
    fi
  fi
fi

# ─── Host triple ─────────────────────────────────────────────────────────────

TARGET_TRIPLE="$(rustc -Vv | awk '/^host:/ {print $2}')"
[[ -n "$TARGET_TRIPLE" ]] \
  || die "could not detect target triple from rustc -Vv"
info "host triple: $TARGET_TRIPLE"

# ─── Backend browser SPA ──────────────────────────────────────────────────────

if [[ ! -d "$BACKEND_SPA_DIST" ]]; then
  info "browser SPA dist missing; building squirrel-web-ui..."
  (cd "$REPO_ROOT" && pnpm -F squirrel-web-ui build) \
    || die "backend SPA build failed"
fi
[[ -d "$BACKEND_SPA_DIST" ]] \
  || die "backend SPA dist still missing after build: $BACKEND_SPA_DIST"
ok "backend SPA present at apps/backend/app/dist/"

# ─── PyInstaller — arm64 slice ───────────────────────────────────────────────

info "building arm64 slice..."
ARM64_DIST="$PYINSTALLER_DIST/slices/arm64"
ARM64_BUILD="$PYINSTALLER_BUILD/arm64"

if [[ "$HOST_ARCH" == "arm64" ]]; then
  PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" \
    pyinstaller \
      --onefile \
      --name squirrel-backend \
      --distpath "$ARM64_DIST" \
      --workpath "$ARM64_BUILD" \
      --specpath "$ARM64_BUILD" \
      --paths "$CLI_LIB" \
      --add-data "$BACKEND_SPA_DIST:app/dist" \
      --clean \
      --noconfirm \
      "$BACKEND_PY" >/dev/null
else
  mkdir -p "$ARM64_DIST" "$ARM64_BUILD"
  PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" \
    arch -arm64 pyinstaller \
      --onefile \
      --name squirrel-backend \
      --distpath "$ARM64_DIST" \
      --workpath "$ARM64_BUILD" \
      --specpath "$ARM64_BUILD" \
      --paths "$CLI_LIB" \
      --add-data "$BACKEND_SPA_DIST:app/dist" \
      --clean \
      --noconfirm \
      "$BACKEND_PY" >/dev/null
fi

ARM64_BIN="$ARM64_DIST/squirrel-backend"
[[ -f "$ARM64_BIN" ]] || die "arm64 slice not produced at $ARM64_BIN"
ok "arm64 slice → $ARM64_BIN ($(du -h "$ARM64_BIN" | cut -f1))"

# ─── Strip extended attributes (R-1.5) ───────────────────────────────────────
xattr -cr "$ARM64_BIN"

if (( ARM64_ONLY )); then
  # ─── arm64-only: copy the single slice directly as the sidecar ───────────────
  mkdir -p "$BIN_OUT_DIR"
  OUT_BIN="$BIN_OUT_DIR/squirrel-backend-$TARGET_TRIPLE"
  cp "$ARM64_BIN" "$OUT_BIN"
  chmod +x "$OUT_BIN"
  ok "arm64 sidecar at apps/desktop/src-tauri/bin/squirrel-backend-$TARGET_TRIPLE"
  say ""
  ok "backend sidecar ready for tauri bundle (arm64-only)"
else
  # ─── PyInstaller — x86_64 slice ──────────────────────────────────────────────
  info "building x86_64 slice..."
  X86_DIST="$PYINSTALLER_DIST/slices/x86_64"
  X86_BUILD="$PYINSTALLER_BUILD/x86_64"

  if [[ "$HOST_ARCH" == "arm64" ]]; then
    mkdir -p "$X86_DIST" "$X86_BUILD"
    PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" \
      arch -x86_64 pyinstaller \
        --onefile \
        --name squirrel-backend \
        --distpath "$X86_DIST" \
        --workpath "$X86_BUILD" \
        --specpath "$X86_BUILD" \
        --paths "$CLI_LIB" \
        --add-data "$BACKEND_SPA_DIST:app/dist" \
        --clean \
        --noconfirm \
        "$BACKEND_PY" >/dev/null
  else
    PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" \
      pyinstaller \
        --onefile \
        --name squirrel-backend \
        --distpath "$X86_DIST" \
        --workpath "$X86_BUILD" \
        --specpath "$X86_BUILD" \
        --paths "$CLI_LIB" \
        --add-data "$BACKEND_SPA_DIST:app/dist" \
        --clean \
        --noconfirm \
        "$BACKEND_PY" >/dev/null
  fi

  X86_BIN="$X86_DIST/squirrel-backend"
  [[ -f "$X86_BIN" ]] || die "x86_64 slice not produced at $X86_BIN"
  ok "x86_64 slice → $X86_BIN ($(du -h "$X86_BIN" | cut -f1))"
  xattr -cr "$X86_BIN"

  # ─── Lipo — create universal binary ──────────────────────────────────────────
  # The Tauri universal build target is `universal-apple-darwin`, so Tauri's
  # externalBin resolution looks for `squirrel-backend-universal-apple-darwin`
  # in src-tauri/bin/. Using the host triple (e.g. aarch64-apple-darwin) causes
  # the sidecar to be silently omitted from the .app bundle.
  info "creating universal binary..."
  mkdir -p "$BIN_OUT_DIR"
  OUT_BIN="$BIN_OUT_DIR/squirrel-backend-universal-apple-darwin"

  lipo -create -output "$OUT_BIN" "$ARM64_BIN" "$X86_BIN"
  chmod +x "$OUT_BIN"

  ACTUAL_ARCHS="$(lipo -archs "$OUT_BIN")"
  [[ "$ACTUAL_ARCHS" == "arm64 x86_64" ]] \
    || die "unexpected archs in universal binary: '$ACTUAL_ARCHS' (expected 'arm64 x86_64')"

  ok "universal sidecar at apps/desktop/src-tauri/bin/squirrel-backend-universal-apple-darwin (archs: $ACTUAL_ARCHS)"
  say ""
  ok "backend sidecar ready for tauri bundle"
fi
