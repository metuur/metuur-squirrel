# Squirrel — top-level dev workflow.
#
# Most install operations still go through ./install.sh (interactive TUI).
# This Makefile is for fast iteration on individual companions during dev.
#
# Web UI:
#   make web-start         → squirrel web start
#   make web-stop          → squirrel web stop
#   make web-status        → squirrel web status
#   make web-build         → rebuild the React bundle (companions/web-ui/app)
#
# Menu bar app:
#   make menubar-build     → compile the native .app into companions/menubar-app/bin
#   make menubar-run       → build + run in the foreground (logs to terminal)
#   make menubar-install   → build + copy to ~/Applications + load LaunchAgent
#   make menubar-uninstall → unload + remove from ~/Applications
#   make menubar-reinstall → menubar-uninstall + menubar-install
#   make menubar-logs      → tail ~/.squirrel/menubar.log
#   make menubar-clean     → wipe the compiled bundle + rasterized icons
#
# All:
#   make build             → menubar-build (extend here as more components add builds)
#   make clean             → menubar-clean

ROOT       := $(CURDIR)
MENUBAR    := $(ROOT)/companions/menubar-app
WEB_APP    := $(ROOT)/companions/web-ui/app

.PHONY: help build clean \
        web-start web-stop web-status web-build \
        menubar-build menubar-run menubar-install menubar-uninstall menubar-reinstall menubar-logs menubar-clean

help:
	@awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' $(MAKEFILE_LIST)

# ─── Web UI ─────────────────────────────────────────────────────────────────

web-start:
	@squirrel web start

web-stop:
	@squirrel web stop

web-status:
	@squirrel web status

web-build:
	@cd $(WEB_APP) && npm run build

# ─── Menu bar app ───────────────────────────────────────────────────────────

menubar-build:
	@$(MAKE) -C $(MENUBAR) build

menubar-run:
	@$(MAKE) -C $(MENUBAR) run

menubar-install:
	@$(MAKE) -C $(MENUBAR) install

menubar-uninstall:
	@$(MAKE) -C $(MENUBAR) uninstall

menubar-reinstall:
	@$(MAKE) -C $(MENUBAR) reinstall

menubar-logs:
	@$(MAKE) -C $(MENUBAR) logs

menubar-clean:
	@$(MAKE) -C $(MENUBAR) clean

# ─── Aggregates ─────────────────────────────────────────────────────────────

build: menubar-build

clean: menubar-clean
