#!/usr/bin/env bash
# scripts/build-dmg.sh — Builds the Squirrel macOS *full-stack* installer DMG.
#
# Squirrel has two distribution paths. Pick the right one for your audience.
#
#   1. THIS SCRIPT — `scripts/build-dmg.sh` → squirrel-installer-macos.dmg
#      Ships: squirrel CLI binary, squirrel-backend binary, agent-pack/
#      (Claude/Codex skills + commands + hooks), plist template, and an
#      `Install Squirrel` script that wires launchd + ~/.squirrel/config.toml.
#      Use for: power users who want CLI access, terminal workflows, and
#      Claude Code / Codex agent integration alongside the desktop popup.
#
#   2. TAURI APP — `cd apps/desktop && pnpm tauri build` → Squirrel.app + .dmg
#      Ships: just the desktop popup with the bundled squirrel-backend
#      sidecar (PyInstaller via apps/desktop/scripts/build-backend-sidecar.sh,
#      wired in tauri.conf.json's `bundle.externalBin`). The Tauri supervisor
#      owns the backend lifecycle.
#      Use for: end users who just want the tray popup. No CLI, no
#      agent-pack, no terminal required after install.
#
# The two .app/.dmg artifacts can coexist on the same machine — the Tauri
# app's bundled backend and the build-dmg.sh backend both bind 127.0.0.1:3939,
# so only one can run at a time. The supervisor's port-probe will adopt
# whichever started first.
#
# Usage:
#   ./scripts/build-dmg.sh            # build squirrel-installer-macos.dmg
#   ./scripts/build-dmg.sh --dry-run  # print steps without executing
#
# Prerequisites (dev machine only — NOT required by end users):
#   pip install pyinstaller
#   pnpm install
#
# Output:
#   squirrel-installer-macos.dmg

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
BUILD="$ROOT/build/pyinstaller"
STAGING="$ROOT/dmg-staging"
DMG_OUT="$ROOT/squirrel-installer-macos.dmg"
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) printf 'Unknown arg: %s\n' "$arg" >&2; exit 1 ;;
  esac
done

# ─── Colors ──────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_GREEN=$'\033[32m'; C_BLUE=$'\033[34m'; C_BOLD=$'\033[1m'
  C_RED=$'\033[31m'; C_RESET=$'\033[0m'
else
  C_GREEN=''; C_BLUE=''; C_BOLD=''; C_RED=''; C_RESET=''
fi
say()  { printf '%s\n' "$*"; }
ok()   { printf '%s✓  %s%s\n' "$C_GREEN" "$*" "$C_RESET"; }
info() { printf '%s   %s%s\n' "$C_BLUE" "$*" "$C_RESET"; }
hdr()  { printf '\n%s=== %s ===%s\n' "$C_BOLD" "$*" "$C_RESET"; }
die()  { printf '%s✗  %s%s\n' "$C_RED" "$*" "$C_RESET" >&2; exit 1; }
run()  { info "$*"; (( DRY_RUN )) || eval "$*"; }

# ─── Version (read from CLI pyproject.toml) ───────────────────────────────────
VERSION="$(grep '^version' "$ROOT/apps/cli/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')"
say ""
printf '%s🐿  Building Squirrel v%s installer%s\n' "$C_BOLD" "$VERSION" "$C_RESET"
(( DRY_RUN )) && printf '%s    (dry-run — no files written)%s\n' "$C_BOLD" "$C_RESET"

# ─── Preflight ───────────────────────────────────────────────────────────────
hdr "Preflight"
command -v pyinstaller >/dev/null 2>&1 || die "pyinstaller not found — run: pip install pyinstaller"
command -v pnpm        >/dev/null 2>&1 || die "pnpm not found — see https://pnpm.io"
command -v hdiutil     >/dev/null 2>&1 || die "hdiutil not found (macOS only)"
ok "pyinstaller, pnpm, hdiutil available"

# ─── Step 1: Build React SPA ─────────────────────────────────────────────────
hdr "Step 1 — Build React SPA"
run "pnpm -F squirrel-web-ui build"
if (( ! DRY_RUN )); then
  [[ -d "$ROOT/apps/backend/app/dist" ]] || die "SPA build failed — apps/backend/app/dist missing"
fi
ok "SPA built → apps/backend/app/dist/"

# ─── Step 2: CLI binary ───────────────────────────────────────────────────────
hdr "Step 2 — Compile CLI binary (squirrel)"
run "pyinstaller \
  --onefile \
  --name squirrel \
  --distpath '$DIST' \
  --workpath '$BUILD/cli' \
  --specpath '$BUILD' \
  --paths '$ROOT/apps/cli/lib' \
  --clean \
  '$ROOT/apps/cli/squirrel'"
if (( ! DRY_RUN )); then
  [[ -f "$DIST/squirrel" ]] || die "CLI binary missing at $DIST/squirrel"
fi
ok "CLI binary → dist/squirrel"

# ─── Step 3: Backend binary ───────────────────────────────────────────────────
hdr "Step 3 — Compile backend binary (squirrel-backend)"
# app/dist is embedded so the binary is fully self-contained (no separate web files needed).
run "pyinstaller \
  --onefile \
  --name squirrel-backend \
  --distpath '$DIST' \
  --workpath '$BUILD/backend' \
  --specpath '$BUILD' \
  --paths '$ROOT/apps/cli/lib' \
  --add-data '$ROOT/apps/backend/app/dist:app/dist' \
  --clean \
  '$ROOT/apps/backend/server.py'"
if (( ! DRY_RUN )); then
  [[ -f "$DIST/squirrel-backend" ]] || die "Backend binary missing at $DIST/squirrel-backend"
fi
ok "Backend binary → dist/squirrel-backend"

# ─── Step 4: Assemble DMG staging ────────────────────────────────────────────
hdr "Step 4 — Assemble DMG staging"
run "rm -rf '$STAGING'"
run "mkdir -p '$STAGING/bin' '$STAGING/resources'"

# Binaries
run "cp '$DIST/squirrel'         '$STAGING/bin/squirrel'"
run "cp '$DIST/squirrel-backend' '$STAGING/bin/squirrel-backend'"

# Agent-pack (skills, commands, hooks for all agents)
run "cp -r '$ROOT/agent-pack' '$STAGING/agent-pack'"

# Resources the end-user installer needs
run "cp '$ROOT/apps/backend/launchd/plist.template' '$STAGING/resources/plist.template'"
run "cp '$ROOT/agent-pack/config/squirrel.toml.example' '$STAGING/resources/squirrel.toml.example'"

# Version file (read by installer for upgrade detection)
(( DRY_RUN )) || printf '%s\n' "$VERSION" > "$STAGING/VERSION"

# End-user installer script (the thing the user actually runs)
run "cp '$ROOT/installer/install.sh' '$STAGING/Install Squirrel'"
run "chmod +x '$STAGING/Install Squirrel'"

ok "Staging assembled → dmg-staging/"

# ─── Step 5: Create DMG ───────────────────────────────────────────────────────
hdr "Step 5 — Create DMG"
run "rm -f '$DMG_OUT'"
run "hdiutil create \
  -volname 'Squirrel $VERSION' \
  -srcfolder '$STAGING' \
  -ov \
  -format UDZO \
  '$DMG_OUT'"
ok "DMG created → squirrel-installer-macos.dmg"

say ""
printf '%sDone.%s  Distribute: %s\n' "$C_BOLD" "$C_RESET" "squirrel-installer-macos.dmg"
printf '       Size: %s\n' "$(du -sh "$DMG_OUT" 2>/dev/null | cut -f1 || echo "n/a (dry-run)")"
say ""
