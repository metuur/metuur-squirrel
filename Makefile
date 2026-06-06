# Squirrel — top-level dev workflow.
#
# Tauri desktop:
#   make dev               → pnpm tauri dev (assumes backend already running)
#   make dev-all           → preflight check + dev (warns if backend offline)
#   make build             → pnpm tauri build
#
# CLI (apps/cli, Python stdlib, no deps):
#   make test-cli          → python3 -m unittest discover -s apps/cli/tests
#   make sq ARGS='...'     → python3 apps/cli/squirrel ARGS
#
# Backend (apps/backend, Python stdlib, depends on apps/cli/lib):
#   make backend-start     → python3 apps/backend/server.py --port 3939
#   make backend-build     → pnpm -F squirrel-web-ui build
#   make backend-dev-ui    → pnpm -F squirrel-web-ui dev
#
# Installer (macOS DMG, dev machine only — requires pyinstaller):
#   make build-installers  → compile binaries + assemble squirrel-installer-macos.dmg
#
# Phase 2 dev workflow:
#   1. Backend runs separately. The user's launchd plist may already serve
#      port 3939 (org.squirrel.web-ui); if so, `make dev` Just Works.
#      Otherwise: `make backend-start` in a second terminal.
#   2. `make dev` (or `make dev-all`) launches the Tauri popup against it.

ROOT := $(CURDIR)
DMG_STAGING := $(ROOT)/dmg-staging
DMG_OUT     := $(ROOT)/squirrel-installer-macos.dmg

.PHONY: help dev dev-all build test-cli sq backend-start backend-build backend-dev-ui \
        build-installers build-installers-arm64 _build-binaries _assemble-dmg

help:
	@awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' $(MAKEFILE_LIST)

# ─── Desktop ────────────────────────────────────────────────────────────────

dev:
	pnpm tauri dev

# Preflight: warn (don't block) if the backend isn't reachable. The popup
# itself shows the offline banner; this is just a nicer dev experience.
dev-all:
	@if curl -sf -o /dev/null --max-time 1 http://127.0.0.1:3939/api/me; then \
		echo "✓ backend reachable on http://127.0.0.1:3939"; \
	else \
		echo "⚠ backend NOT reachable on http://127.0.0.1:3939"; \
		echo "  Start it in another terminal:  make backend-start"; \
		echo "  Popup will show the offline banner until then."; \
	fi
	pnpm tauri dev

build:
	pnpm tauri build

# ─── CLI ────────────────────────────────────────────────────────────────────

test-cli:
	cd $(ROOT)/apps/cli && python3 -m unittest discover -s tests -v

sq:
	@python3 $(ROOT)/apps/cli/squirrel $(ARGS)

# ─── Backend ────────────────────────────────────────────────────────────────

backend-start:
	python3 $(ROOT)/apps/backend/server.py --port 3939

backend-build:
	pnpm -F squirrel-web-ui build

backend-dev-ui:
	pnpm -F squirrel-web-ui dev

# ─── Installer (macOS DMG) ───────────────────────────────────────────────────

# Produces squirrel-installer-macos.dmg.
# Requires: pip install pyinstaller  (dev machine only — not shipped to users)
build-installers:
	bash $(ROOT)/scripts/build-dmg.sh

# arm64-only build (skips x86_64 slice + lipo). Use on Apple Silicon when you
# don't have an x86_64-capable Python. Result won't run on Intel Macs.
build-installers-arm64:
	bash $(ROOT)/scripts/build-dmg.sh --arm64-only

build-installers-dry:
	bash $(ROOT)/scripts/build-dmg.sh --dry-run

# Produces squirrel-manual-install-<version>.zip (no signing required).
# Compiles all three apps (CLI, backend, desktop) and bundles install-manual.sh.
build-manual-zip:
	bash $(ROOT)/scripts/build-manual-zip.sh

# Re-use existing artifacts (faster, for re-packaging after a dmg build).
build-manual-zip-fast:
	bash $(ROOT)/scripts/build-manual-zip.sh --skip-build

build-manual-zip-dry:
	bash $(ROOT)/scripts/build-manual-zip.sh --dry-run
