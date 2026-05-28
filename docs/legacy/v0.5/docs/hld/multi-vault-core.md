# Multi-Vault Core — High-Level Design

## Overview

Squirrel today binds every interface (slash commands, the `squirrel` CLI, all skills) to a single vault path configured at `~/.squirrel/config.toml: vault_path`. Users with more than one context (personal projects, work projects, client projects, paperwork) must edit the config file every time they switch. This change introduces a first-class **multi-vault** configuration: an ordered list of named vaults, one marked default, with `--vault NAME` selection on every interface that touches a vault. It ships independently of any UI work and benefits slash-command and CLI users immediately. Single-vault users keep their current setup with zero behavior change via lazy automatic migration.

## Stakeholders & Impact

- **Power users (Squirrel developers, the project author, technical adopters).** They juggle work and personal projects today by manually editing config or maintaining shell aliases that swap files. After this ships they configure each context once, pick the active one via `--vault NAME`, and never edit config to switch again.
- **Future Web UI users** (next spec — `web-ui-simple`). Multi-vault in core is a prerequisite for the UI's vault switcher; building the UI without this would create a parallel, divergent vault model.
- **Slash-command users on Codex / Cursor.** Today they suffer the same limitation. Same benefit.
- **Single-vault users.** Get auto-migration. Notice nothing.
- **Out of audience.** Non-technical end users (spouse, 60-year-old described in the web UI spec). They see exactly one vault for the rest of their lives; the multi-vault machinery exists but is hidden from them.

## Goals

- **G1 — Multi-vault config schema.** `config.toml` supports an ordered `[[vaults]]` array; each entry has `name`, `path`, and `default` (boolean). Exactly one is default.
- **G2 — Universal selector.** Every CLI subcommand, slash command, and skill that reads or writes the vault accepts `--vault NAME`. Omitted → default vault.
- **G3 — Lazy migration.** The first Squirrel tool that loads a legacy single-vault config after upgrade rewrites the file in place to the new schema, idempotently, with no user action.
- **G4 — Per-vault state.** `~/.squirrel/state.json` becomes `~/.squirrel/state/<vault-name>.json`. The current project, current intent, and switch ledger are tracked separately per vault.
- **G5 — Vault management commands.** New `squirrel vaults` subcommand group: `list`, `add NAME PATH`, `remove NAME`, `default NAME`.
- **G6 — Zero regression.** Every existing test passes unchanged. Every existing slash command and CLI invocation produces identical output for single-vault users.
- **G7 — Stdlib only.** No new Python dependencies. TOML parsing uses `tomllib` on 3.11+ with a hand-rolled fallback for 3.9/3.10.

## Non-Goals

- **N1 — Web UI.** Covered in the separate `web-ui-simple` spec. This change is prerequisite, not coupled.
- **N2 — Vault content migration between machines.** The existing sync protocol (`/sq-sync-out`, `/sq-sync-in`) is unchanged.
- **N3 — Cross-vault search or reporting.** Each vault is queried independently. Cross-vault views are a future concern.
- **N4 — Renaming vaults in place.** v1 only supports add / remove / set-default. Rename is "remove + add" (with manual state file move).
- **N5 — Sharing one config across machines.** Each machine has its own `~/.squirrel/config.toml`. The new schema does not change that.
- **N6 — Validating vault contents at add-time.** `squirrel vaults add NAME PATH` checks the path exists and is a directory; it does not require PARA structure to already be present.

## Success Criteria

- **S1.** A user with the legacy `vault_path = "~/vault-tdah"` config runs any Squirrel command after upgrade; the config is rewritten with a `[[vaults]]` array containing one default entry. Subsequent runs do not re-migrate.
- **S2.** A user runs `squirrel vaults add work ~/work-vault` and `squirrel vaults list` shows two vaults, one marked `(default)`.
- **S3.** A user runs `squirrel status --vault work` and gets the status of the work vault; `squirrel status` (no flag) returns the default vault's status. Both commands produce the same output format as before.
- **S4.** A user runs `/sq-where-am-i --vault personal` from a slash command and gets the personal vault's loading note.
- **S5.** A user runs `squirrel vaults remove work` while `work` is default; the command refuses with a message saying to set another default first.
- **S6.** A user has both vaults active in different shells simultaneously; per-vault state files do not collide.
- **S7.** All existing tests in `tests/` pass without modification.
- **S8.** The migration is observable by checking the top of `config.toml` for a `# Auto-migrated <ISO-date>` comment line.
- **S9.** A user removes the `[[vaults]]` block by mistake and reverts to the legacy `vault_path` field; on next run the migration runs again, idempotently. (Robustness against config hand-edits.)
- **S10.** Running `squirrel vaults add` with a path that does not exist produces a clear error and does not modify the config.
