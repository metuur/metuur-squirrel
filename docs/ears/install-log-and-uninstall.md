# Install Log & Uninstall Script — EARS Specifications

## Unit 1: Install snapshot tool (`installer/install-snapshot.sh`)

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN invoked as `install-snapshot.sh <before\|after> <logfile> <installer-id> <version>`, THE SYSTEM SHALL append one snapshot section to `<logfile>` containing the phase, an ISO-8601 UTC timestamp, the installer id, the installer version, and the macOS product version. |
| R-1.2 | THE SYSTEM SHALL record, for every path in the Squirrel footprint inventory (LLD list), either `MISSING` or its metadata: type, size, permissions, owner, mtime, and sha256 for regular files; entry count and total size for directories. |
| R-1.3 | THE SYSTEM SHALL never write the contents of any inspected file into the log (metadata and hashes only). |
| R-1.4 | IF a regular file exceeds 10 MB or is a live database or log file (`state/squirrel.db*`, `*.log`), THE SYSTEM SHALL skip hashing it and record its size and metadata only. |
| R-1.5 | THE SYSTEM SHALL record environment diagnostics: launchd state of `org.squirrel.web-ui`, any TCP listener on port 3939 (command, pid, executable path), codesign identity and quarantine xattr for the app bundle and all four binary paths, `command -v squirrel`, the value of `PATH`, and running `Squirrel`/`squirrel-backend` processes. |
| R-1.6 | IF any individual probe or stat fails, THE SYSTEM SHALL record `unavailable` for that item and continue. |
| R-1.7 | THE SYSTEM SHALL always exit with status 0, so a snapshot failure can never fail an installation. |
| R-1.8 | WHEN the `before` phase runs, THE SYSTEM SHALL create `~/.squirrel/install-logs/` if missing; WHEN the `after` phase completes, THE SYSTEM SHALL retain only the 10 newest install logs in that directory (never deleting the current run's log), deleting older ones. |

## Unit 2: Installer integration

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the `.pkg` installer runs, THE SYSTEM SHALL write the BEFORE snapshot from a new `preinstall` script and the AFTER snapshot at the end of `postinstall`, both into the same log file, executing as the console user so the log lands in that user's `~/.squirrel/install-logs/`. |
| R-2.1a | IF the console user cannot be resolved or any snapshot step fails, THE SYSTEM SHALL skip logging and exit the `preinstall`/`postinstall` snapshot section with status 0 — snapshot integration SHALL never cause an installer (any of the three) to fail. |
| R-2.2 | WHEN `installer/install.sh` (drag-install DMG) runs, THE SYSTEM SHALL write the BEFORE snapshot after upgrade detection and before any filesystem change, and the AFTER snapshot as its final step, into one log file with installer id `dmg`. |
| R-2.3 | WHEN `installer/install-manual.sh` runs, THE SYSTEM SHALL write BEFORE and AFTER snapshots the same way with installer id `manual`. |
| R-2.4 | THE SYSTEM SHALL name each install log `<UTC-timestamp>-<installer-id>.log` under `~/.squirrel/install-logs/`. |
| R-2.5 | WHERE the build scripts package installers (`build-pkg.sh`, `build-dmg.sh`, manual zip packaging), THE SYSTEM SHALL ship `install-snapshot.sh` alongside the installer scripts and `uninstall.sh` in the distributed artifact (pkg payload at `/usr/local/share/squirrel/uninstall.sh`; DMG and zip alongside the install scripts). |

## Unit 3: Uninstaller — vault preservation

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN `uninstall.sh` starts, THE SYSTEM SHALL read every `[[vaults]] path` from `~/.squirrel/config.toml` (tilde-expanded) into a preserve list before deleting or modifying anything, matching only uncommented `path` keys inside `[[vaults]]` tables (never commented-out lines or `path` keys from other tables). |
| R-3.2 | IF `~/.squirrel/config.toml` is missing or unparsable, THE SYSTEM SHALL warn, proceed with an empty preserve list, and still delete only footprint paths. |
| R-3.3 | THE SYSTEM SHALL never delete, create, or modify any file or directory inside any preserved vault path, including the vault's `.squirrel/` subfolder. |
| R-3.4 | IF any removal target equals, contains, or is contained within a preserved vault path, THE SYSTEM SHALL abort with an error before deleting anything — comparing fully canonicalized paths (symlinks resolved, trailing slashes stripped) on both the preserve list and every removal target. |
| R-3.4a | THE SYSTEM SHALL delete removal targets by their literal enumerated paths without dereferencing symlinks, and SHALL include an automated test exercising the vault gate with a symlinked vault and a vault configured inside `~/.squirrel`. |
| R-3.5 | WHEN the uninstall completes, THE SYSTEM SHALL print a summary listing every preserved vault path. |

## Unit 4: Uninstaller — removal coverage

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL stop running instances before removal, in this order: quit/kill the `Squirrel` app, then `launchctl bootout` the `org.squirrel.web-ui` service (so `KeepAlive` cannot respawn the backend), and only then kill any remaining `squirrel-backend` process, verifying afterwards that no listener remains on port 3939. |
| R-4.2 | THE SYSTEM SHALL remove, when present: `~/Library/LaunchAgents/org.squirrel.web-ui.plist`, `~/.local/bin/squirrel{,-backend}` and their `.bak` files, `~/.claude/plugins/squirrel`, `~/.codex/squirrel`, `~/.cursor/rules/squirrel`, `~/.windsurf/rules/squirrel`, and all `~/Library/{Application Support,Caches,WebKit,HTTPStorages}/com.metuur.squirrel{,.dev}`, `~/Library/Preferences/com.metuur.squirrel{,.dev}.plist`, and `~/Library/Saved Application State/com.metuur.squirrel{,.dev}.savedState` paths. |
| R-4.3 | IF `~/.claude/plugins/installed_plugins.json` exists and registers `squirrel@squirrel`, THE SYSTEM SHALL remove that entry while leaving all other entries intact, writing the result atomically (temp file + rename); IF the file cannot be parsed, THE SYSTEM SHALL leave it unmodified and warn rather than risk corrupting other plugins' registration. |
| R-4.4 | IF any root-owned target exists (`/Applications/Squirrel.app`, `/usr/local/bin/squirrel{,-backend}`, `/usr/local/share/squirrel`), THE SYSTEM SHALL remove them via a single `sudo` batch; IF none exist, THE SYSTEM SHALL not invoke `sudo` at all. |
| R-4.5 | THE SYSTEM SHALL remove `~/.squirrel/` last, after all other removals have been attempted. |
| R-4.6 | IF an individual removal fails, THE SYSTEM SHALL report it, continue with remaining targets, and exit non-zero with the failures listed in the summary. |
| R-4.7 | THE SYSTEM SHALL leave shell rc files untouched and, IF `~/.zshrc` or `~/.bash_profile` contains an `export PATH=...$HOME/.local/bin...` line, print a note that it was left in place. |

## Unit 5: Uninstaller — safety & UX

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | IF run on a non-macOS system or as root, THE SYSTEM SHALL exit with an error before doing anything. |
| R-5.2 | WHEN invoked, THE SYSTEM SHALL print the full removal plan (only paths that exist) and the preserve list before any change. |
| R-5.3 | WHERE `--dry-run` is passed, THE SYSTEM SHALL print the plan and exit 0 without modifying the filesystem. |
| R-5.4 | THE SYSTEM SHALL require explicit interactive confirmation before deleting, unless `--yes` is passed. |
| R-5.5 | THE SYSTEM SHALL tee its full output to `/tmp/squirrel-uninstall-<UTC-timestamp>.log`. |
| R-5.6 | THE SYSTEM SHALL only remove explicitly enumerated footprint paths — no wildcard deletion outside the `com.metuur.squirrel{,.dev}` Library entries. |
| R-5.7 | WHERE the footprint path list is duplicated across `install-snapshot.sh` and `uninstall.sh`, THE SYSTEM SHALL mark each copy with an identical sync-sentinel comment and provide an automated check that the lists match. |
