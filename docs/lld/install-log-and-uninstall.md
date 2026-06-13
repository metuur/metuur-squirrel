# Install Log & Uninstall Script — Low-Level Design

## Architecture

### New files
| File | Purpose |
|------|---------|
| `installer/install-snapshot.sh` | Self-contained snapshot tool: `install-snapshot.sh <before\|after> <logfile> <installer-id> <version>`. Appends one snapshot section to the log. |
| `installer/uninstall.sh` | Self-contained uninstaller covering all three footprints. Flags: `--dry-run`, `--yes`. |
| `installer/pkg/scripts/preinstall` | New `.pkg` script: writes the BEFORE snapshot (as console user) before payload is laid down. |

### Modified files
| File | Change |
|------|--------|
| `installer/pkg/scripts/postinstall` | Append AFTER snapshot at the end (after launch steps). |
| `installer/install.sh` | Call snapshot `before` right after upgrade detection, `after` as the final step. |
| `installer/install-manual.sh` | Same two calls. |
| `scripts/build-pkg.sh` | Copy `install-snapshot.sh` into the pkg scripts dir (next to pre/postinstall) and `uninstall.sh` into the payload at `/usr/local/share/squirrel/uninstall.sh`. |
| `scripts/build-dmg.sh` | Include `install-snapshot.sh` and `uninstall.sh` next to `install.sh` in the DMG. |
| zip packaging (wherever `install-manual.sh` is bundled) | Include both scripts. |
| `README.md`, `apps/backend/app/src/pages/GuidePage.tsx` | Replace manual uninstall recipes with a pointer to `uninstall.sh`. |

### Install log
- **Location:** `~/.squirrel/install-logs/<UTC-ts>-<installer-id>.log` where `installer-id` ∈ `pkg|dmg|manual` and ts is `date -u +%Y%m%dT%H%M%SZ`. The BEFORE call creates the file (and dir) and the AFTER call appends to the same file — the caller passes the same logfile path to both phases (pkg: preinstall exports the path to a marker file `~/.squirrel/install-logs/.current` that postinstall reads and removes; shell installers just hold it in a variable).
- **Retention:** after writing, keep the newest 10 logs in the dir, delete older ones (`ls -t | tail -n +11`).
- **Snapshot section format** (plain text, house style: ISO-8601 UTC, `printf`, no colors when not a TTY):
  - Header: phase, timestamp, installer id, installer version, `sw_vers` product version, hostname-free (no PII beyond `$HOME` paths).
  - **Path inventory** — for each path in the footprint list below: `MISSING` or `type size perms owner mtime sha256(first-8)` for files; `entries=<n> bytes=<total>` for dirs. **Never file contents.** Skip hashing files >10 MB (record size only).
  - **Environment** — `launchctl print gui/$(id -u)/org.squirrel.web-ui` (state line only, or `not loaded`); port 3939 listener via `lsof -nP -iTCP:3939 -sTCP:LISTEN` (command, pid, exe path); `codesign -dv` identity line + `xattr -p com.apple.quarantine` for `/Applications/Squirrel.app`, `~/.local/bin/squirrel{,-backend}`, `/usr/local/bin/squirrel{,-backend}`; `command -v squirrel`; `$PATH`; running `Squirrel`/`squirrel-backend` processes (`pgrep -lf`). **The whole `[environment]` section is piped through a `--token <hex> → REDACTED` filter** because the app-managed backend carries its per-launch token in argv (`backend_supervisor.rs:234-243`), so `pgrep -fl` would otherwise leak it into the log — the metadata-only rule (R-1.3) must hold for process args too, not just file contents.
- **Footprint path list** (the union from the research inventory): `/Applications/Squirrel.app`, `/usr/local/bin/squirrel`, `/usr/local/bin/squirrel-backend`, `/usr/local/share/squirrel`, `~/.local/bin/squirrel`, `~/.local/bin/squirrel-backend`, `~/Library/LaunchAgents/org.squirrel.web-ui.plist`, `~/.squirrel` (dir summary) plus key children (`config.toml`, `version`, `launchd-token` — metadata only, `state/squirrel.db`, `logs/squirrel.log`, `web-ui.log`), `~/.claude/plugins/squirrel`, `~/.codex/squirrel`, `~/.cursor/rules/squirrel`, `~/.windsurf/rules/squirrel`, and `~/Library/{Application Support,Caches,WebKit,HTTPStorages}/com.metuur.squirrel{,.dev}`, `~/Library/Preferences/com.metuur.squirrel{,.dev}.plist`, `~/Library/Saved Application State/com.metuur.squirrel{,.dev}.savedState`.
- **pkg root/user split:** `preinstall`/`postinstall` run as root; both invoke the snapshot script the same way `postinstall` already writes user state — `sudo -u "$CONSOLE_USER"` with `HOME` resolved from `dscl`, so the log lands in the user's `~/.squirrel/install-logs/`.

### Uninstaller flow (`installer/uninstall.sh`)
1. **Guards:** macOS only; refuse to run as root (it `sudo`s selectively); parse `--dry-run`/`--yes`.
2. **Enumerate vaults first:** parse every `[[vaults]] path` from `~/.squirrel/config.toml` (grep/sed, tilde-expanded) into a PRESERVE list before anything is deleted. Config missing → empty list, proceed.
3. **Build removal plan** from the footprint list above (only entries that exist), partitioned into user-owned and root-owned (`/Applications/Squirrel.app` owner-dependent, `/usr/local/*`). Print plan + PRESERVE list. `--dry-run` stops here. Otherwise require typed `y` confirmation unless `--yes`.
4. **Vault safety gate:** before any `rm`, assert no removal target equals, contains, or is contained in any PRESERVE path (string-prefix check on physical paths via `cd && pwd -P` where the path exists). Violation → abort with error, delete nothing.
5. **Stop everything:** `osascript -e 'quit app "Squirrel"'` (best-effort) then `pkill -x Squirrel`; `launchctl bootout gui/$(id -u)/org.squirrel.web-ui`; `pkill -f squirrel-backend`. Brief wait/recheck. (Mirrors `postinstall:87-101`, the only known-good retire sequence.)
6. **Remove, user scope:** launchd plist, `~/.local/bin/squirrel{,-backend}{,.bak}`, agent packs (4 dirs), `squirrel@squirrel` entry from `~/.claude/plugins/installed_plugins.json` (python3, same approach as `install-manual.sh` registration; file absent → skip), all `com.metuur.squirrel{,.dev}` Library paths, and **last** `~/.squirrel/` (it holds the config that named the vaults and this run's logs).
7. **Remove, root scope:** only if any root-owned target exists, a single `sudo rm -rf` batch for `/Applications/Squirrel.app`, `/usr/local/bin/squirrel{,-backend}`, `/usr/local/share/squirrel`. No sudo prompt when nothing system-wide is installed.
8. **Logging & summary:** `tee` all output to `/tmp/squirrel-uninstall-<UTC-ts>.log` (not `$HOME` — the point is leaving nothing behind; `/tmp` is OS-cleaned). Final summary: what was removed, the preserved vault paths, and a note that shell-rc `PATH` lines (if `install-manual.sh` added one) were left in place.

## Constraints
- macOS only; Bash 3.2-compatible (system bash), `set -euo pipefail`, house style helpers (`ok/info/warn/die`, TTY-conditional colors) duplicated per script — matching the existing convention of self-contained installer scripts (no sourced shared lib, so each artifact ships standalone).
- Install log must never contain file contents or secrets — metadata/hash only. The launchd token (64-hex) and `squirrel.log` (historically leaked tokens, audit H1) are the named threats.
- `preinstall`/`postinstall` run as root; all user-side writes must go through the existing `CONSOLE_USER` + `dscl`-HOME pattern.
- Snapshot must be non-fatal: any failing probe (`lsof` absent, `codesign` error) records `unavailable` and continues — an install must never fail because logging failed. The snapshot script always exits 0.
- The uninstaller must work when only *some* footprints exist (partial/mixed installs) and when `config.toml` is missing or unparsable (warn, treat as zero vaults — deleting `~/.squirrel` is then still safe because vaults never live inside it).

## Key Decisions
- **Metadata-only snapshots** (user-confirmed): eliminates the redaction problem entirely instead of solving it.
- **Squirrel paths + environment diagnostics** (user-confirmed): the 2026-06-12 "Backend offline" incident was only diagnosable from launchd/port/token-mismatch state — path inventory alone would have missed it.
- **One uninstaller for all three footprints** (user-confirmed): detection by existence; conditional sudo keeps the common per-user case prompt-free.
- **Vaults byte-for-byte untouched, including `<vault>/.squirrel/`** (user-confirmed): smallest blast radius; the uninstaller never writes inside a vault.
- **Self-contained scripts, duplicated helpers** over a sourced lib: matches the existing 4-script convention and keeps each distributed artifact (pkg scripts dir, DMG, zip) standalone.
- **Uninstall log to `/tmp`, install logs to `~/.squirrel/install-logs/`**: install logs belong with app data (and are removed by uninstall, after this run's plan is already printed); the uninstall log must survive `~/.squirrel` deletion without leaving new clutter in `$HOME`.
- **Leave rc-file PATH edits** : removing a generic `export PATH="$HOME/.local/bin:$PATH"` line could break other tools; print a note instead.
- **`.pkg` BEFORE snapshot via new `preinstall` script**: `postinstall` runs after the payload is laid down, so it cannot capture pre-install state; `pkgbuild` natively supports a `preinstall` script in the same scripts dir.

## Out of Scope
- Fixing the launchd `KeepAlive` upgrade bug itself (research addendum root cause B) — separate change; the install log only makes it diagnosable.
- `bump_version.py` TARGETS fix for `agent-pack/.claude-plugin/plugin.json` (addendum root cause A) — separate, surgical change.
- A `squirrel doctor` diagnostics command (floated in 2026-06-10 pre-mortem research) — the snapshot script is a stepping stone, not the feature.
- Log rotation for `~/.squirrel/logs/squirrel.log` — pre-existing issue, untouched.
