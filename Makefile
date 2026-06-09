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
	deploy-pages \
        build-installers build-installers-arm64 build-pkg build-pkg-fast build-pkg-dry \
        _maybe-bump _build-binaries _assemble-dmg

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

deploy-pages:
	npx wrangler pages deploy ./landing/pages --project-name squirrel --commit-dirty=true

# ─── Installer (macOS DMG) ───────────────────────────────────────────────────

# Produces squirrel-installer-macos.dmg.
# Requires: pip install pyinstaller  (dev machine only — not shipped to users)
# Optional version bump: `make build-installers BUMP=patch` (or minor/major)
# syncs every manifest to the new version before building. No BUMP → no change.
BUMP ?=

_maybe-bump:
	@if [ -n "$(BUMP)" ]; then python3 $(ROOT)/scripts/bump_version.py $(BUMP); fi

build-installers: _maybe-bump
	bash $(ROOT)/scripts/build-dmg.sh

# arm64-only build (skips x86_64 slice + lipo). Use on Apple Silicon when you
# don't have an x86_64-capable Python. Result won't run on Intel Macs.
build-installers-arm64: _maybe-bump
	bash $(ROOT)/scripts/build-dmg.sh --arm64-only

build-installers-dry:
	bash $(ROOT)/scripts/build-dmg.sh --dry-run

# ─── All-in-one installer (macOS .pkg) — Apple Silicon only ──────────────────
# Guided double-click installer: desktop app + CLI + agent-pack, auto-configured.
# arm64-only: avoids the universal (x86_64) slice + lipo, which can't be produced
# on an Apple Silicon machine without an x86_64 Python toolchain.
#   make build-pkg [BUMP=patch|minor]  → fresh arm64 app + CLI binaries, then package
#   make build-pkg-fast                → reuse existing arm64 app + dist/ binaries
#   make build-pkg-dry                 → print steps without executing
# With BUMP, build-pkg recompiles so the .pkg version matches its contents.
# (build-pkg-fast reuses prior artifacts — do NOT combine it with BUMP.)
# build-dmg.sh runs with --skip-dmg here: build-pkg only needs its dist/ CLI
# binaries, not the manual drag-install DMG. The single public artifact is
# squirrel-macos.dmg (the .pkg wrapped in a DMG) from build-pkg.sh.
build-pkg: _maybe-bump
	# Remove stale Squirrel.app bundles from every target tree BEFORE building.
	# Cargo's incremental cache + the --target split mean a leftover bundle from a
	# prior (or differently-targeted) build can survive and get packaged instead
	# of the fresh one — that's why installs kept shipping an old version. Clearing
	# them first guarantees the only Squirrel.app present afterwards is this build's.
	rm -rf $(ROOT)/target/aarch64-apple-darwin/release/bundle/macos/Squirrel.app \
	       $(ROOT)/target/release/bundle/macos/Squirrel.app \
	       $(ROOT)/apps/desktop/src-tauri/target/aarch64-apple-darwin/release/bundle/macos/Squirrel.app \
	       $(ROOT)/apps/desktop/src-tauri/target/release/bundle/macos/Squirrel.app
	TAURI_TARGET=aarch64-apple-darwin pnpm -F @squirrel/desktop tauri:build
	bash $(ROOT)/scripts/build-dmg.sh --arm64-only --skip-dmg
	bash $(ROOT)/scripts/build-pkg.sh --skip-build --arm64-only

build-pkg-fast: _maybe-bump
	bash $(ROOT)/scripts/build-pkg.sh --skip-build --arm64-only

build-pkg-dry:
	bash $(ROOT)/scripts/build-pkg.sh --dry-run --arm64-only

# Produces squirrel-manual-install-<version>.zip (no signing required).
# Compiles all three apps (CLI, backend, desktop) and bundles install-manual.sh.
build-manual-zip:
	bash $(ROOT)/scripts/build-manual-zip.sh

# Re-use existing artifacts (faster, for re-packaging after a dmg build).
build-manual-zip-fast:
	bash $(ROOT)/scripts/build-manual-zip.sh --skip-build

build-manual-zip-dry:
	bash $(ROOT)/scripts/build-manual-zip.sh --dry-run
