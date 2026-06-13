# Install Log & Uninstall Script — High-Level Design

## Overview

Two operational tools for the Squirrel macOS distribution. First, an **install log**: every installer run (`.pkg` postflight, drag-install DMG `install.sh`, manual zip `install-manual.sh`) writes a timestamped log capturing system state **before** and **after** installation — Squirrel-owned filesystem paths (metadata only, never contents) plus environment diagnostics (launchd service status, port 3939 listener, code-signing/quarantine state, PATH). Second, an **uninstall script**: a single user-runnable script that removes every Squirrel file across all three installer footprints — binaries, app bundle, launchd service, token, agent packs, macOS Library dirs, and `~/.squirrel/` — while leaving every vault 100% untouched.

## Stakeholders & Impact

- **End users with broken installs** — today an upgrade-over-existing can leave a stale launchd backend fighting the new app ("Backend offline", web-UI `v?`; see research addendum 2026-06-12). There is no record of what the system looked like before/after install, so diagnosis requires live forensics. After this ships, the install log answers "what was already there?" in one file.
- **Maintainer (Javier)** — can ask a user for a single log file instead of walking them through `launchctl`/`lsof`/`codesign` commands.
- **Users removing Squirrel** — today uninstall is a fragmented set of printed recipes (README, GuidePage, `install-manual.sh` epilogue) and partial commands (`squirrel web uninstall` removes the daemon only). After this ships, one script removes everything except their notes.
- **Secondary consumers** — README/GuidePage uninstall instructions get replaced by a pointer to the script; the `.pkg`/DMG/zip build scripts ship the new scripts as payload.

## Goals

- Every run of any of the three installers produces a timestamped install log under `~/.squirrel/install-logs/` containing a BEFORE snapshot, an AFTER snapshot, and the installer's identity/version.
- Snapshots cover all Squirrel-owned destination paths (per the research footprint inventory) **and** environment diagnostics: `org.squirrel.web-ui` launchd status, port 3939 listener identity, codesign/quarantine state of app and binaries, `command -v squirrel`, PATH, OS version.
- Snapshots record **metadata only** (existence, type, size, perms, owner, mtime, sha256) — file contents are never copied, so the launchd token and anything inside `squirrel.log`/`config.toml` can never leak into the install log.
- One uninstall script handles **all three footprints** in a single run: `.pkg` system paths (with `sudo` only when needed), DMG/manual per-user paths, launchd service + token, agent packs, Claude plugin registration, and macOS Library dirs (including `.dev` variants).
- The uninstaller reads every `[[vaults]] path` from `~/.squirrel/config.toml` **before** deleting anything, and never writes or deletes inside any vault — including `<vault>/.squirrel/`.
- The uninstaller supports `--dry-run` (print plan, change nothing) and requires explicit confirmation before deleting (skippable with `--yes`).

## Non-Goals

- No telemetry, remote upload, or crash reporting — all logs stay local (existing invariant).
- No in-app "reset"/"uninstall" UI and no new CLI subcommand — this is a standalone script (existing `squirrel web uninstall` is unchanged).
- No pruning of `<vault>/.squirrel/` (manifests, switches, applied/, audit-logs/) — vaults are left byte-for-byte untouched.
- No removal of shell-rc `PATH` edits made by `install-manual.sh` — the uninstaller prints a note instead of editing user rc files.
- No Windows/Linux support — macOS only, matching the installers.
- No change to what the installers actually install; they only gain logging calls.

## Success Criteria

- Running any installer on a clean machine and on a machine with a prior install produces a log whose BEFORE section visibly differs (e.g. the second run shows the existing `~/.squirrel/version`, launchd service, and port 3939 listener).
- `grep`-ing any generated install log for the launchd token value finds nothing, by construction (no file contents are ever embedded).
- After running the uninstaller on a machine with any of the three install types: `command -v squirrel` is empty, no `org.squirrel.web-ui` service is loaded, no `squirrel-backend` process runs, no Squirrel path from the footprint inventory exists — and every vault directory listed in the pre-deletion `config.toml` still exists with identical contents (including `<vault>/.squirrel/`).
- `uninstall.sh --dry-run` exits without modifying the filesystem (verifiable by before/after snapshot).
