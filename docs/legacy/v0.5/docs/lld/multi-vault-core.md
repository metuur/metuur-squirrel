# Multi-Vault Core — Low-Level Design

## Architecture

```
                ┌─────────────────────────────────────────────────────┐
                │  ~/.squirrel/config.toml                            │
                │  [[vaults]] name="personal" path="~/vault-tdah"     │
                │  [[vaults]] name="work"     path="~/work-vault"     │
                │                       default=true on exactly one   │
                └────────────────────────┬────────────────────────────┘
                                         │
                                         ▼
                ┌─────────────────────────────────────────────────────┐
                │  lib/config_loader.py  (NEW)                        │
                │  list_vaults() / get_vault(name) /                  │
                │  get_default_vault() / add_vault / remove_vault /   │
                │  set_default / migrate_legacy / _validate           │
                └────────────────────────┬────────────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
   ┌──────────────────┐      ┌──────────────────┐       ┌──────────────────┐
   │  squirrel CLI    │      │  Slash commands  │       │  Skills          │
   │  --vault NAME    │      │  --vault NAME    │       │  pass-through    │
   └────────┬─────────┘      └────────┬─────────┘       └────────┬─────────┘
            │                         │                          │
            └─────────────────────────┴──────────────────────────┘
                                      │
                                      ▼
                ┌─────────────────────────────────────────────────────┐
                │  lib/  (status_aggregator, deadline_scanner, ...)   │
                │  unchanged — already take a vault path              │
                └────────────────────────┬────────────────────────────┘
                                         │
                ┌────────────────────────┴────────────────────────────┐
                │  ~/.squirrel/state/<vault-name>.json                │
                │  per-vault current project, current intent,         │
                │  switch ledger                                      │
                └─────────────────────────────────────────────────────┘
```

The lever is `lib/config_loader.py`. Every caller — CLI, slash command, future UI — funnels through it. Migration, validation, and resolution live in one module.

## Components

### New

| File | Purpose | Approx LoC |
|---|---|---|
| `lib/config_loader.py` | TOML load + migration + vault list + lookup | 250 |
| `tests/test_config_loader.py` | Migration idempotence, validation errors, default handling | 200 |

### Modified

| File | Change |
|---|---|
| `~/.squirrel/config.toml` schema | Add `[[vaults]]` array; rename `environment_name` → `machine_environment` |
| `~/.squirrel/state.json` location | Move to `~/.squirrel/state/<vault-name>.json` |
| `squirrel` CLI | Add `--vault NAME` to `status`, `deadlines`, `recover`, `dashboard`; add new `vaults` subcommand group |
| `lib/session_scanner.py` | Read new schema; per-vault state path |
| `lib/switch_tracker.py` | Per-vault state path |
| `lib/package_protocol.py` | Read `machine_environment` (renamed) |
| `lib/dashboard_generator.py` | Optional `vault_name` for title |
| `commands/sq-status.md` | Accept `--vault NAME` arg, pass to underlying script |
| `commands/sq-deadlines.md` | Same |
| `commands/sq-where-am-i.md` | Same |
| `commands/sq-start.md` | Same |
| `commands/sq-end.md` | Same |
| `commands/sq-capture.md` | Same |
| `commands/sq-brief.md` | Same |
| `commands/sq-decision.md` | Same |
| `commands/sq-recover.md` | Same |
| `commands/sq-chunk.md` | Vault-independent → no change |
| `commands/sq-estimate.md` | Vault-independent → no change |
| `commands/sq-chunk-intent.md` | Add `--vault NAME` |
| `commands/sq-task-initiation.md` | Add `--vault NAME` |
| `commands/sq-parakeet.md` | Add `--vault NAME` |
| `commands/sq-dashboard.md` | Add `--vault NAME` |
| `commands/sq-sync-out.md` | Add `--vault NAME` |
| `commands/sq-sync-in.md` | Add `--vault NAME` |
| `commands/sq-init.md` | Add `--add-vault` subflow |
| `skills/*/SKILL.md` | Document optional `vault_name` argument; pass `--vault` to script calls |
| `INSTALL.md` | Document multi-vault setup |
| `docs/guides/getting-started.md` | Add a "Multiple vaults" section |

### Unchanged

- `lib/intent_parser.py`, `lib/status_aggregator.py`, `lib/deadline_scanner.py`, `lib/chunk_helper.py`, `lib/estimate_buffer.py`, `lib/tag_parser.py` — already take a vault path as parameter
- All test fixtures in `tests/fixtures/`
- The 24 (or more) existing tests in `tests/`

## Config schema

### Legacy (still works via migration)

```toml
vault_path = "~/vault-tdah"
environment_name = "personal"
default_email = "user@example.com"

[projects]
active = [...]

[compliance]
strict = false
# ...
```

### New schema (post-migration)

```toml
# Auto-migrated 2026-05-25
default_email = "user@example.com"
machine_environment = "personal"   # was: environment_name

[[vaults]]
name = "personal"
path = "~/vault-tdah"
default = true

[[vaults]]
name = "work"
path = "~/work-vault"
default = false

[projects]
active = [...]

[compliance]
strict = false
# ...
```

### Migration algorithm (in `migrate_legacy`)

1. Read the file as text. Parse as TOML.
2. If `[[vaults]]` (parsed key `vaults` with list value) already exists, return — no migration.
3. If `vault_path` is missing, return — there's nothing to migrate; the config is broken and the caller will surface the appropriate error.
4. Build the new vault entry:
   - `name` = `environment_name` if set, else `"default"`
   - `path` = `vault_path`
   - `default` = `true`
5. Rewrite the file:
   - Preserve every existing non-migrated line and comment.
   - Delete the `vault_path` line.
   - Rename `environment_name` line to `machine_environment` (preserving the value).
   - Insert the `[[vaults]]` block after the top-level scalar keys, before any other `[section]`.
   - Prepend the comment `# Auto-migrated <ISO-date>` as the very first line.
6. Migrate the state file: if `~/.squirrel/state.json` exists, ensure `~/.squirrel/state/` exists and move the file to `~/.squirrel/state/<default-vault-name>.json`.

The implementation rewrites the file in place atomically (temp file + `os.replace`).

## Vault resolution

`get_vault(name=None)` returns a `Vault` namedtuple with `name: str` and `path: Path`.

- If `name` is provided: look up by name in the `[[vaults]]` array. Not found → raise `VaultNotFoundError` listing valid names.
- If `name` is None: return the entry with `default = true`. Multiple defaults → raise `ConfigError`. Zero defaults → raise `ConfigError`.
- If `[[vaults]]` is empty: raise `NoVaultsConfiguredError` with hint about `/sq-init` or `squirrel vaults add`.

`list_vaults()` returns `list[Vault]` in config order, including the default flag.

## CLI surface

### New: `squirrel vaults` subcommand group

```
squirrel vaults list
squirrel vaults add NAME PATH
squirrel vaults remove NAME
squirrel vaults default NAME
```

Validation rules:

- `add NAME PATH`: reject if `NAME` already in use, if `PATH` does not exist, or if `PATH` is not a directory. Validation lives in `config_loader.add_vault()`, not in the CLI handler — so future UI / API callers benefit from the same checks.
- `remove NAME`: reject if `NAME` is the default vault. Caller must `default <other>` first.
- `default NAME`: clear default flag on every other vault, set on `NAME`. Reject if `NAME` not found.
- All four commands fail-loud with non-zero exit code and a one-line error on stderr.

### Modified: existing subcommands gain `--vault NAME`

`status`, `deadlines`, `recover`, `dashboard` all accept an optional `--vault NAME`. Default = the configured default vault.

`chunk` and `estimate` are vault-independent — no change.

`install` is vault-independent — no change.

## Slash command updates

Every `commands/sq-*.md` file that reads or writes the vault gains an optional `--vault NAME` argument parsed from `$ARGUMENTS`. The bash blocks inside each command file are updated to:

1. Extract `--vault NAME` from `$ARGUMENTS` (using a small awk/sed pattern).
2. Pass `--vault "$VAULT_NAME"` to the underlying Python script call.
3. If `--vault` was not provided, the script defaults via `config_loader.get_default_vault()` — same behavior as today.

`commands/sq-init.md` adds an `--add-vault` flag that runs an interactive subflow (name, path, set-as-default y/n).

## Skill updates

Each `skills/*/SKILL.md` that consumes a vault is updated to:

- Document `vault_name` as an optional argument in its frontmatter description.
- When invoked, if `vault_name` is present, append `--vault $vault_name` to every `python3 lib/...` call inside the skill.

The skills do not change behavior otherwise. Skills that don't touch the vault (`chunk-intent`, `task-initiation`'s protocol selection, `parakeet`'s tone selection — but their data source does touch the vault) need careful audit. The audit rule: if the skill or any script it invokes reads or writes vault files, it accepts `vault_name`.

## State files per vault

Today: `~/.squirrel/state.json` holds:
- `current_project`
- `current_intent`
- `last_switch_at`
- `switch_ledger` (recent context switches)

After: `~/.squirrel/state/<vault-name>.json`. Same schema per file.

`session_scanner.py` and `switch_tracker.py` are updated to accept a vault name and resolve to the corresponding state file. Helper: `lib/config_loader.state_file_for(vault_name) -> Path`.

## Constraints

### Hard

- **C1.** Python stdlib only. `tomllib` on 3.11+; hand-rolled minimal TOML parser for 3.9/3.10 (already exists in `squirrel` CLI for `vault_path`; refactor and reuse).
- **C2.** Python 3.9, 3.10, 3.11, 3.12 must all pass tests.
- **C3.** Migration is idempotent: running it twice on the same file is a no-op after the first run.
- **C4.** Atomic config rewrites: temp file + `os.replace`.
- **C5.** All existing tests continue to pass without modification. Where a test currently writes a single-vault config, the test is unchanged — the migration handles it on load.
- **C6.** Single-vault users see zero output change. Their `config.toml` is rewritten on first load, but every subcommand they ran before produces byte-identical results.

### Soft

- **C7.** Validation lives in `lib/config_loader.py`, not in callers. CLI handlers thinly wrap the lib calls.
- **C8.** Error messages name the bad input and the valid options. "Vault 'wrok' not found. Available: personal, work, client-a."
- **C9.** Pass-through `--vault` in slash commands is the same parsing pattern used today for `--level` etc. — copy that pattern, don't invent a new one.

## Key Decisions

### D1 — Lazy migration over explicit command

Migration runs in-process the first time any tool loads the legacy config after upgrade. Users never run `squirrel migrate`. Rationale: explicit migration commands fail silently for users who don't think to run them; lazy migration is unmissable.

Rejected alternative: explicit `squirrel migrate` command.

### D2 — Per-vault state files, not a single state file with vault keys

Each vault gets `~/.squirrel/state/<vault-name>.json`. Rationale: per-file isolation prevents concurrent-write collisions when two shells operate on different vaults. Single-file would need locking.

Rejected alternative: single state file with top-level vault keys.

### D3 — Validation in `lib/config_loader.py`, not CLI

`add_vault` / `remove_vault` / `set_default` perform all validation in `lib/config_loader.py`. CLI handlers are thin wrappers. Rationale: when the web UI calls these, the rules are enforced consistently without duplicating logic.

Rejected alternative: CLI does validation, lib functions trust inputs.

### D4 — `--vault` flag, not `SQUIRREL_VAULT` env var

Explicit CLI flag wins. Rationale: a flag is visible in command history and scripts; an env var hides which vault produced an output, making logs and screenshots ambiguous.

Rejected alternative: `SQUIRREL_VAULT=work squirrel status`. (Could still be added later as a fallback if user demand exists.)

### D5 — `[[vaults]]` ordering preserved

The order of `[[vaults]]` entries in config is preserved in `list_vaults()` output and in any UI list. Default vault is not necessarily first. Rationale: users sort by their own logic; we don't reorder.

### D6 — `default = true` is a boolean flag per entry, not a separate top-level `default_vault` field

Storing the default flag inside the entry keeps the schema self-describing. Cost: must validate that exactly one is true.

Rejected alternative: top-level `default_vault = "personal"`. Cleaner to enforce but more fragile when entries are removed.

### D7 — Renames are out of scope

Renaming a vault means renaming the entry, the state file, and possibly references in compliance config (`allowed_inbound_environments`). Too much surface for v1. Workaround: `remove old; add new`.

### D8 — Ship before any web UI work

This spec ships fully before any code in `companions/web-ui/`. De-risks the UI by proving multi-vault works under existing interfaces first.

## Out of Scope

- Web UI integration (separate spec)
- Cross-vault search or aggregated reports
- Vault rename
- Sharing config across machines
- Environment variable overrides for vault selection
- Vault aliases / tags / grouping
- Per-vault encryption keys (sync compliance is per-machine, not per-vault)
- Vault discovery (auto-finding vaults on disk)
