# Squirrel — top-level dev workflow.
#
# Tauri desktop (Phase 1):
#   make dev               → pnpm tauri dev
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

ROOT := $(CURDIR)

.PHONY: help dev build test-cli sq backend-start backend-build backend-dev-ui

help:
	@awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' $(MAKEFILE_LIST)

# ─── Desktop ────────────────────────────────────────────────────────────────

dev:
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
