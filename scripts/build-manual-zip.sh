#!/usr/bin/env bash
#
# scripts/build-manual-zip.sh — Build squirrel-manual-install-<version>.zip
#
# Compiles (or re-uses) the three app artifacts:
#   apps/cli      → dist/squirrel            (PyInstaller, universal)
#   apps/backend  → dist/squirrel-backend    (PyInstaller, universal)
#   apps/desktop  → Squirrel.app             (Tauri, universal)
#
# Then packages them with the agent-pack and a self-contained installer into a
# zip users can unzip and run without Gatekeeper or signing requirements.
#
# Usage:
#   ./scripts/build-manual-zip.sh               # build everything fresh
#   ./scripts/build-manual-zip.sh --skip-build  # skip compile, use existing artifacts
#   ./scripts/build-manual-zip.sh --no-app      # exclude the Tauri .app bundle
#   ./scripts/build-manual-zip.sh --arm64-only  # single-arch (faster dev iteration)
#   ./scripts/build-manual-zip.sh --dry-run     # print steps, write nothing
#
# Output: squirrel-manual-install-<version>.zip
#
# Zip contents:
#   squirrel-manual-install/
#     install-manual.sh         ← self-contained no-signing installer
#     VERSION
#     bin/
#       squirrel                ← CLI (universal)
#       squirrel-backend        ← web UI daemon (universal)
#     Squirrel.app/             ← Tauri desktop app (drag to /Applications) — optional
#     agent-pack/               ← skills, commands, lib, hooks, templates
#     resources/
#       squirrel.toml.example

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ─── Flags ────────────────────────────────────────────────────────────────────
SKIP_BUILD=0
INCLUDE_APP=1
ARM64_ONLY=0
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --skip-build)  SKIP_BUILD=1 ;;
    --no-app)      INCLUDE_APP=0 ;;
    --arm64-only)  ARM64_ONLY=1 ;;
    --dry-run)     DRY_RUN=1 ;;
    --help|-h)     sed -n '1,28p' "$0"; exit 0 ;;
    *) printf 'Unknown arg: %s\n' "$arg" >&2; exit 1 ;;
  esac
done

# ─── Colors ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'
  C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_BLUE=''; C_BOLD=''; C_YELLOW=''; C_RED=''; C_RESET=''
fi
ok()   { printf '%s✓  %s%s\n' "$C_GREEN"  "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE"   "$*" "$C_RESET"; }
warn() { printf '%s⚠  %s%s\n' "$C_YELLOW" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED"    "$*" "$C_RESET" >&2; exit 1; }
hdr()  { printf '\n%s── %s ──%s\n' "$C_BOLD" "$*" "$C_RESET"; }
run()  { info "$*"; (( DRY_RUN )) || eval "$*"; }

# ─── Artifact paths ───────────────────────────────────────────────────────────
CLI_BIN="$ROOT/dist/squirrel"
BACKEND_BIN="$ROOT/dist/squirrel-backend"
# Tauri places bundles differently depending on target:
#   universal build  → apps/desktop/src-tauri/target/universal-apple-darwin/release/bundle/macos/
#   aarch64 build    → target/release/bundle/macos/  (workspace root, no arch prefix)
TAURI_TARGET_UNIVERSAL="$ROOT/apps/desktop/src-tauri/target/universal-apple-darwin/release/bundle/macos/Squirrel.app"
TAURI_TARGET_ARM64_PREFIXED="$ROOT/apps/desktop/src-tauri/target/aarch64-apple-darwin/release/bundle/macos/Squirrel.app"
TAURI_TARGET_ARM64_ROOT="$ROOT/target/release/bundle/macos/Squirrel.app"

VERSION="$(grep '^version' "$ROOT/apps/cli/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')"
ZIP_NAME="squirrel-manual-install-${VERSION}.zip"
ZIP_OUT="$ROOT/$ZIP_NAME"
STAGING_DIR="$ROOT/build/manual-zip-staging"
ZIP_ROOT="$STAGING_DIR/squirrel-manual-install"

printf '\n%s🐿  Squirrel v%s — manual install zip%s\n' "$C_BOLD" "$VERSION" "$C_RESET"
(( DRY_RUN )) && warn "dry-run mode — no files written"
say ""

# ─── Step 1: Build apps/backend (React SPA → squirrel-web-ui) ─────────────────
hdr "Step 1 — Backend SPA (squirrel-web-ui)"
SPA_DIST="$ROOT/apps/backend/app/dist"
if [[ -d "$SPA_DIST" ]] && (( SKIP_BUILD )); then
  ok "SPA already built — skipping (--skip-build)"
else
  run "pnpm -F squirrel-web-ui build"
  if (( ! DRY_RUN )); then
    [[ -d "$SPA_DIST" ]] || die "SPA build failed — $SPA_DIST missing"
  fi
  ok "SPA built → apps/backend/app/dist/"
fi

# ─── Step 2: Build apps/cli → squirrel (PyInstaller) ─────────────────────────
hdr "Step 2 — CLI binary (apps/cli → dist/squirrel)"

_build_cli_slice() {
  local arch="$1"
  local dist="$ROOT/dist/slices/cli/$arch"
  local build="$ROOT/build/pyinstaller/cli-$arch"
  mkdir -p "$dist" "$build"
  local -a cmd=(
    pyinstaller --onefile --name squirrel
    --distpath "$dist" --workpath "$build" --specpath "$build"
    --paths "$ROOT/apps/cli/lib"
    --clean --noconfirm
    "$ROOT/apps/cli/squirrel"
  )
  if [[ "$arch" == "x86_64" && "$(uname -m)" == "arm64" ]]; then
    PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" arch -x86_64 "${cmd[@]}" >/dev/null
  elif [[ "$arch" == "arm64" && "$(uname -m)" == "x86_64" ]]; then
    PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" arch -arm64 "${cmd[@]}" >/dev/null
  else
    PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" "${cmd[@]}" >/dev/null
  fi
  xattr -cr "$dist/squirrel"
  echo "$dist/squirrel"
}

if [[ -f "$CLI_BIN" ]] && (( SKIP_BUILD )); then
  ok "CLI binary already built — skipping (--skip-build): $CLI_BIN"
else
  command -v pyinstaller >/dev/null 2>&1 || die "pyinstaller not found — run: pip install pyinstaller"
  if (( DRY_RUN )); then
    info "would build CLI: pyinstaller apps/cli/squirrel → dist/squirrel"
  else
    mkdir -p "$ROOT/dist"
    if (( ARM64_ONLY )); then
      _build_cli_slice arm64
      cp "$ROOT/dist/slices/cli/arm64/squirrel" "$CLI_BIN"
      warn "arm64-only mode — binary is not universal"
    else
      [[ "$(uname -m)" == "arm64" ]] && \
        { arch -x86_64 /usr/bin/true 2>/dev/null || die "Rosetta required for universal build. Run: softwareupdate --install-rosetta"; }
      _build_cli_slice arm64
      _build_cli_slice x86_64
      lipo -create -output "$CLI_BIN" \
        "$ROOT/dist/slices/cli/arm64/squirrel" \
        "$ROOT/dist/slices/cli/x86_64/squirrel"
      ARCHS="$(lipo -archs "$CLI_BIN")"
      [[ "$ARCHS" == "arm64 x86_64" ]] || die "CLI lipo failed — got archs: $ARCHS"
    fi
  fi
  ok "CLI binary → dist/squirrel"
fi

# ─── Step 3: Build apps/backend → squirrel-backend (PyInstaller) ─────────────
hdr "Step 3 — Backend daemon (apps/backend → dist/squirrel-backend)"

_build_backend_slice() {
  local arch="$1"
  local dist="$ROOT/dist/slices/backend/$arch"
  local build="$ROOT/build/pyinstaller/backend-$arch"
  mkdir -p "$dist" "$build"
  local -a cmd=(
    pyinstaller --onefile --name squirrel-backend
    --distpath "$dist" --workpath "$build" --specpath "$build"
    --paths "$ROOT/apps/cli/lib"
    --add-data "$SPA_DIST:app/dist"
    --clean --noconfirm
    "$ROOT/apps/backend/server.py"
  )
  if [[ "$arch" == "x86_64" && "$(uname -m)" == "arm64" ]]; then
    PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" arch -x86_64 "${cmd[@]}" >/dev/null
  elif [[ "$arch" == "arm64" && "$(uname -m)" == "x86_64" ]]; then
    PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" arch -arm64 "${cmd[@]}" >/dev/null
  else
    PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning" "${cmd[@]}" >/dev/null
  fi
  xattr -cr "$dist/squirrel-backend"
  echo "$dist/squirrel-backend"
}

if [[ -f "$BACKEND_BIN" ]] && (( SKIP_BUILD )); then
  ok "Backend binary already built — skipping (--skip-build): $BACKEND_BIN"
else
  command -v pyinstaller >/dev/null 2>&1 || die "pyinstaller not found — run: pip install pyinstaller"
  if (( DRY_RUN )); then
    info "would build backend: pyinstaller apps/backend/server.py → dist/squirrel-backend"
  else
    mkdir -p "$ROOT/dist"
    if (( ARM64_ONLY )); then
      _build_backend_slice arm64
      cp "$ROOT/dist/slices/backend/arm64/squirrel-backend" "$BACKEND_BIN"
      warn "arm64-only mode — binary is not universal"
    else
      _build_backend_slice arm64
      _build_backend_slice x86_64
      lipo -create -output "$BACKEND_BIN" \
        "$ROOT/dist/slices/backend/arm64/squirrel-backend" \
        "$ROOT/dist/slices/backend/x86_64/squirrel-backend"
      ARCHS="$(lipo -archs "$BACKEND_BIN")"
      [[ "$ARCHS" == "arm64 x86_64" ]] || die "backend lipo failed — got archs: $ARCHS"
    fi
  fi
  ok "Backend binary → dist/squirrel-backend"
fi

# ─── Step 4: Build apps/desktop → Squirrel.app (Tauri) ───────────────────────
if (( INCLUDE_APP )); then
  hdr "Step 4 — Desktop app (apps/desktop → Squirrel.app)"

  # Locate the .app — check all known output locations
  _find_app() {
    for candidate in \
      "$TAURI_TARGET_UNIVERSAL" \
      "$TAURI_TARGET_ARM64_PREFIXED" \
      "$TAURI_TARGET_ARM64_ROOT"; do
      [[ -d "$candidate" ]] && { echo "$candidate"; return; }
    done
  }

  if [[ -n "$(_find_app)" ]] && (( SKIP_BUILD )); then
    ok "Squirrel.app already built — skipping (--skip-build)"
  else
    command -v pnpm >/dev/null 2>&1 || die "pnpm not found"
    if (( DRY_RUN )); then
      info "would build: pnpm tauri build (apps/desktop)"
    else
      # --target is a TAURI flag (before any `--`); passing it after `--` sends it
      # to cargo only, so tauri's bundler can't find the binary in target/<triple>.
      if (( ARM64_ONLY )); then
        (cd "$ROOT/apps/desktop" && SQUIRREL_ARM64_ONLY=1 pnpm tauri build --target aarch64-apple-darwin)
      else
        (cd "$ROOT/apps/desktop" && pnpm tauri build --target universal-apple-darwin)
      fi
    fi
    APP_PATH="$(_find_app)"
    if (( ! DRY_RUN )); then
      [[ -d "$APP_PATH" ]] || die "Tauri build succeeded but Squirrel.app not found at expected path"
    fi
    ok "Squirrel.app built → $APP_PATH"
  fi
fi

# ─── Step 5: Assemble staging ─────────────────────────────────────────────────
hdr "Step 5 — Assemble"
run "rm -rf '$STAGING_DIR'"
run "mkdir -p '$ZIP_ROOT/bin' '$ZIP_ROOT/resources'"

# Binaries
if (( ! DRY_RUN )); then
  [[ -f "$CLI_BIN"     ]] || die "CLI binary missing: $CLI_BIN (run without --skip-build)"
  [[ -f "$BACKEND_BIN" ]] || die "Backend binary missing: $BACKEND_BIN (run without --skip-build)"
fi
run "cp '$CLI_BIN'     '$ZIP_ROOT/bin/squirrel'"
run "cp '$BACKEND_BIN' '$ZIP_ROOT/bin/squirrel-backend'"
if (( ! DRY_RUN )); then
  chmod +x "$ZIP_ROOT/bin/squirrel" "$ZIP_ROOT/bin/squirrel-backend"
fi
ok "Binaries → bin/"

# Tauri .app
if (( INCLUDE_APP )); then
  APP_PATH="$(_find_app)"
  if (( ! DRY_RUN )); then
    [[ -d "$APP_PATH" ]] || die "Squirrel.app missing — build failed or use --no-app"
    run "cp -r '$APP_PATH' '$ZIP_ROOT/Squirrel.app'"
  else
    info "would copy Squirrel.app → squirrel-manual-install/Squirrel.app"
  fi
  ok "Squirrel.app → Squirrel.app/"
fi

# Agent-pack
AGENT_PACK_SRC="$ROOT/dmg-staging/agent-pack"
[[ -d "$AGENT_PACK_SRC" ]] || die "dmg-staging/agent-pack/ not found"
run "rsync -a --delete '$AGENT_PACK_SRC/' '$ZIP_ROOT/agent-pack/'"
ok "Agent-pack → agent-pack/"

# Config example
CONFIG_EXAMPLE="$ROOT/dmg-staging/resources/squirrel.toml.example"
[[ -f "$CONFIG_EXAMPLE" ]] || CONFIG_EXAMPLE="$ROOT/agent-pack/config/squirrel.toml.example"
if [[ -f "$CONFIG_EXAMPLE" ]]; then
  run "cp '$CONFIG_EXAMPLE' '$ZIP_ROOT/resources/squirrel.toml.example'"
  ok "Config example → resources/"
else
  warn "squirrel.toml.example not found — skipping"
fi

# Installer script
INSTALLER_SRC="$ROOT/installer/install-manual.sh"
[[ -f "$INSTALLER_SRC" ]] || die "installer/install-manual.sh not found"
run "cp '$INSTALLER_SRC' '$ZIP_ROOT/install-manual.sh'"
if (( ! DRY_RUN )); then chmod +x "$ZIP_ROOT/install-manual.sh"; fi
ok "install-manual.sh → /"

# Install-log snapshot tool (install-manual.sh calls it) + the uninstaller.
run "cp '$ROOT/installer/install-snapshot.sh' '$ZIP_ROOT/install-snapshot.sh'"
run "cp '$ROOT/installer/uninstall.sh' '$ZIP_ROOT/uninstall.sh'"
if (( ! DRY_RUN )); then chmod +x "$ZIP_ROOT/install-snapshot.sh" "$ZIP_ROOT/uninstall.sh"; fi
ok "install-snapshot.sh + uninstall.sh → /"

# Entitlements.plist — needed by install-manual.sh to re-sign binaries with
# disable-library-validation so PyInstaller's extracted libpython can be dlopen'd.
ENTITLEMENTS_SRC="$ROOT/apps/desktop/src-tauri/Entitlements.plist"
if [[ -f "$ENTITLEMENTS_SRC" ]]; then
  run "cp '$ENTITLEMENTS_SRC' '$ZIP_ROOT/Entitlements.plist'"
  ok "Entitlements.plist → /"
else
  warn "Entitlements.plist not found — re-sign step in install-manual.sh will be skipped"
fi

# VERSION
run "printf '%s\n' '$VERSION' > '$ZIP_ROOT/VERSION'"
ok "VERSION → $VERSION"

# Strip quarantine from the whole staging area
if (( ! DRY_RUN )); then
  xattr -cr "$STAGING_DIR" 2>/dev/null || true
fi

# ─── Step 6: Show contents ────────────────────────────────────────────────────
hdr "Contents"
if (( ! DRY_RUN )); then
  find "$ZIP_ROOT" \( -name "*.app" -prune -o -print \) | \
    sed "s|$ZIP_ROOT|squirrel-manual-install|" | sort
  if (( INCLUDE_APP )) && [[ -d "$ZIP_ROOT/Squirrel.app" ]]; then
    info "Squirrel.app/ included ($(du -sh "$ZIP_ROOT/Squirrel.app" | cut -f1))"
  fi
fi

# ─── Step 7: Zip ──────────────────────────────────────────────────────────────
hdr "Zip"
run "rm -f '$ZIP_OUT'"
if (( ! DRY_RUN )); then
  (cd "$STAGING_DIR" && zip -r "$ZIP_OUT" squirrel-manual-install --quiet)
fi
if (( ! DRY_RUN )); then
  SIZE="$(du -sh "$ZIP_OUT" | cut -f1)"
  ok "Created: $ZIP_NAME  ($SIZE)"
else
  ok "Would create: $ZIP_NAME"
fi

# ─── Summary ──────────────────────────────────────────────────────────────────
say ""
printf '%s  Done → %s%s\n' "$C_BOLD" "$ZIP_NAME" "$C_RESET"
say ""
say "  User installs with:"
say ""
say "    unzip $ZIP_NAME"
say "    bash squirrel-manual-install/install-manual.sh"
say ""
(( INCLUDE_APP )) && say "  Or drag Squirrel.app to /Applications after unzipping."
say ""
