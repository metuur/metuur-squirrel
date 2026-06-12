# Install Log & Uninstall Script — Tasks

## Unit 1: Install snapshot tool (`installer/install-snapshot.sh`)

- [x] 1.1 Create `installer/install-snapshot.sh` skeleton with CLI contract, house-style helpers, and the footprint path inventory (est: ~45m)
  - acceptance: R-1.1, R-1.2, R-1.3, R-1.4 — `<before|after> <logfile> <installer-id> <version>` appends a section with header (phase, ISO-8601 UTC ts, installer id/version, macOS version) and per-path metadata (`MISSING` or type/size/perms/owner/mtime/sha256 for files, `entries=N bytes=total` for dirs); never file contents; no hashing of >10 MB files or `state/squirrel.db*`/`*.log`
  - verify: Run `before` then `after` on this machine; inspect the log — every footprint path present, no file contents, `launchd-token` shows metadata only; create a 11 MB dummy at a footprint path → size recorded, no hash

- [x] 1.2 Add the environment-diagnostics section and per-probe fault tolerance (deps: 1.1, est: ~40m)
  - acceptance: R-1.5, R-1.6, R-1.7 — launchd state of `org.squirrel.web-ui`, port 3939 listener (cmd/pid/exe), codesign identity + quarantine xattr for app and four binary paths, `command -v squirrel`, `PATH`, running `Squirrel`/`squirrel-backend` processes; any failing probe records `unavailable`; script always exits 0
  - verify: Run with backend up and down — listener section differs; temporarily `PATH=/usr/bin` to break a probe → `unavailable` recorded and exit code is 0

- [x] 1.3 Log directory creation and retention (deps: 1.1, est: ~20m)
  - acceptance: R-1.8 — `before` creates `~/.squirrel/install-logs/` if missing; `after` keeps only the 10 newest logs and never deletes the current run's log
  - verify: Seed 12 dummy logs, run a `before`+`after` pair → 10 remain including the new one; oldest gone

## Unit 2: Installer integration

- [x] 2.1 Wire `install.sh` (drag-DMG) to snapshot before/after (deps: 1.3, est: ~25m)
  - acceptance: R-2.2, R-2.4, R-2.1a — BEFORE after upgrade detection and before any filesystem change, AFTER as final step, same `<UTC-ts>-dmg.log` file; snapshot failure (script missing/unreadable) cannot fail the install
  - verify: Run `install.sh` end-to-end (or with a stubbed payload) → one log with both sections; delete `install-snapshot.sh` and re-run → install completes, no log

- [x] 2.2 Wire `install-manual.sh` the same way with id `manual` (deps: 1.3, est: ~20m)
  - acceptance: R-2.3, R-2.4, R-2.1a
  - verify: Same as 2.1 against `install-manual.sh`

- [ ] 2.3 Add `installer/pkg/scripts/preinstall` and extend `postinstall` for the `.pkg` (deps: 1.3, est: ~45m)
  - acceptance: R-2.1, R-2.1a — preinstall writes BEFORE as console user (CONSOLE_USER + dscl HOME pattern), passes the logfile path via `~/.squirrel/install-logs/.current`; postinstall appends AFTER at its end and removes the marker; unresolvable console user or any snapshot failure → skip silently, exit 0
  - verify: Build the pkg and run `sudo installer -pkg ... -target /` from an SSH/non-GUI session (no console user) → install succeeds with no log; run from GUI → one log in the user's `install-logs/` with both sections

- [ ] 2.4 Ship the new scripts in all three artifacts (deps: 2.1, 2.2, 2.3, 3.4, est: ~30m)
  - acceptance: R-2.5 — `build-pkg.sh` copies `install-snapshot.sh` into the pkg scripts dir and `uninstall.sh` into the payload at `/usr/local/share/squirrel/uninstall.sh`; `build-dmg.sh` and `build-manual-zip.sh` include both scripts alongside the install scripts
  - verify: Build all three artifacts; `pkgutil --expand` / mount DMG / unzip and confirm both scripts present at the specced locations

## Unit 3: Uninstaller — scaffold, vault preservation, safety gate

- [ ] 3.1 Create `installer/uninstall.sh` scaffold: guards, flags, vault enumeration, plan, confirmation (est: ~50m)
  - acceptance: R-5.1, R-5.2, R-5.3, R-5.4, R-3.1, R-3.2 — macOS-only, refuses root; parses `--dry-run`/`--yes`; reads every uncommented `[[vaults]] path` (tilde-expanded, `[[vaults]]` tables only) into the preserve list before anything else; prints removal plan (existing paths only) + preserve list; `--dry-run` exits 0 with no filesystem change; otherwise requires typed confirmation unless `--yes`; missing/unparsable config → warn, empty preserve list
  - verify: `--dry-run` on this machine prints plan + vaults, exits 0, `find`-verified no mtime changes; config with a commented `# path =` line and a `path` key in another table → neither preserved; `sudo uninstall.sh` refuses

- [ ] 3.2 Implement the canonicalized vault safety gate (deps: 3.1, est: ~40m)
  - acceptance: R-3.3, R-3.4, R-3.4a — both preserve list and every removal target canonicalized (symlinks resolved, trailing slashes stripped) before prefix-containment comparison; any overlap aborts before deleting anything; deletions use literal enumerated paths, never dereferencing symlinks
  - verify: Configure a vault via symlink and a vault path inside `~/.squirrel` in a sandbox `$HOME` → both abort with error and nothing deleted

- [ ] 3.3 Automated vault-gate test (deps: 3.2, est: ~40m)
  - acceptance: R-3.4a — repeatable test exercising the gate with (a) a symlinked vault, (b) a vault inside `~/.squirrel`, (c) a normal vault that survives a full run
  - verify: New `tests/installer/test_uninstall_vault_gate.sh` (fake `$HOME` sandbox, never touches the real one) passes; wired as `make test-installer`

## Unit 4: Uninstaller — removal coverage

- [ ] 4.1 Stop-everything sequence (deps: 3.1, est: ~30m)
  - acceptance: R-4.1 — ordered: quit/kill `Squirrel` app → `launchctl bootout gui/$(id -u)/org.squirrel.web-ui` → kill remaining `squirrel-backend` → verify no listener on port 3939
  - verify: With the launchd backend running, run the stop phase → service unloaded, no respawn (KeepAlive defeated), `lsof -iTCP:3939` empty

- [ ] 4.2 User-scope removals (deps: 3.2, 4.1, est: ~45m)
  - acceptance: R-4.2, R-4.3, R-4.5, R-4.6 — removes plist, `~/.local/bin/squirrel{,-backend}{,.bak}`, four agent packs, all `com.metuur.squirrel{,.dev}` Library paths; `installed_plugins.json` entry removed atomically (temp+rename), unparsable JSON → warn and leave untouched; `~/.squirrel/` deleted last; individual failures reported, run continues, exit non-zero with failures in summary
  - verify: Sandbox `$HOME` populated with the full per-user footprint + a decoy plugin entry → everything removed, decoy entry intact, `~/.squirrel` gone last (instrument with `set -x`); corrupt the JSON → file untouched, warning printed

- [ ] 4.3 Root-scope removals via single conditional sudo batch (deps: 4.2, est: ~25m)
  - acceptance: R-4.4 — `/Applications/Squirrel.app`, `/usr/local/bin/squirrel{,-backend}`, `/usr/local/share/squirrel` removed in one `sudo` invocation only when at least one exists; no sudo prompt otherwise
  - verify: Per-user-only sandbox run never prompts for sudo; with a real pkg install present, one sudo prompt removes all system paths

- [ ] 4.4 Output tee, summary, and rc-file note (deps: 4.2, est: ~25m)
  - acceptance: R-5.5, R-3.5, R-4.7 — full output teed to `/tmp/squirrel-uninstall-<UTC-ts>.log`; summary lists removed paths, failures, and every preserved vault; rc files untouched, note printed when an `export PATH=...$HOME/.local/bin...` line exists
  - verify: Run end-to-end in sandbox → `/tmp` log matches stdout; summary names the vault; `~/.zshrc` with the PATH line is byte-identical after the run and the note appears

## Unit 5: Footprint sync & docs

- [ ] 5.1 Footprint sync sentinel + automated check (deps: 1.1, 3.1, est: ~30m)
  - acceptance: R-5.6, R-5.7 — both scripts mark their footprint list with an identical sentinel comment block; a check script extracts and diffs the two lists; only enumerated paths are ever removed (wildcards limited to `com.metuur.squirrel{,.dev}` Library entries)
  - verify: `tests/installer/test_footprint_sync.sh` passes; add a path to one list only → check fails; wired into `make test-installer`

- [ ] 5.2 Replace manual uninstall recipes with a pointer to `uninstall.sh` (deps: 4.4, est: ~20m)
  - acceptance: HLD secondary consumers — `README.md` and `GuidePage.tsx` uninstall sections point at the script (DMG/zip location and `/usr/local/share/squirrel/uninstall.sh`), keeping the vault-is-preserved note
  - verify: README renders correctly; GuidePage builds (`tsc --noEmit`) and shows the new instructions
