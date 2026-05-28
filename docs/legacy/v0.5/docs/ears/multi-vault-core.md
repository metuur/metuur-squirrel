# Multi-Vault Core — EARS Specifications

## Unit 1: Config schema

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL support a TOML array of tables named `[[vaults]]` in `~/.squirrel/config.toml`, where each entry has `name` (string), `path` (string), and `default` (boolean). |
| R-1.2 | THE SYSTEM SHALL require exactly one entry in `[[vaults]]` to have `default = true`. |
| R-1.3 | IF zero or more than one vault entries have `default = true`, THE SYSTEM SHALL raise a `ConfigError` naming the violating count and refuse to load. |
| R-1.4 | THE SYSTEM SHALL require every vault `name` to be unique. |
| R-1.5 | IF two vault entries share a `name`, THE SYSTEM SHALL raise a `ConfigError` naming the duplicate. |
| R-1.6 | THE SYSTEM SHALL expand leading `~` in vault `path` values to the current user's home directory at load time. |
| R-1.7 | THE SYSTEM SHALL rename the legacy top-level `environment_name` field to `machine_environment` during migration. |

## Unit 2: Migration

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN any Squirrel tool loads `~/.squirrel/config.toml` and finds a `vault_path` field with no `[[vaults]]` array, THE SYSTEM SHALL run migration in-process. |
| R-2.2 | WHEN migration runs, THE SYSTEM SHALL build a single vault entry with `name = environment_name` (or `"default"` if absent), `path = vault_path`, `default = true`. |
| R-2.3 | WHEN migration runs, THE SYSTEM SHALL preserve every other top-level field, every other `[section]`, and every existing comment in the file. |
| R-2.4 | WHEN migration runs, THE SYSTEM SHALL delete the `vault_path` line. |
| R-2.5 | WHEN migration runs and `environment_name` exists, THE SYSTEM SHALL rename it to `machine_environment` (preserving the value). |
| R-2.6 | WHEN migration runs, THE SYSTEM SHALL prepend a `# Auto-migrated <ISO-date>` comment as the very first line of the rewritten file. |
| R-2.7 | WHEN migration writes the rewritten file, THE SYSTEM SHALL write to a temporary file in the same directory and call `os.replace` to atomically move it into place. |
| R-2.8 | IF `[[vaults]]` already exists in the file, THE SYSTEM SHALL skip migration and proceed to normal load. |
| R-2.9 | IF `vault_path` is absent AND `[[vaults]]` is absent, THE SYSTEM SHALL not attempt migration; subsequent calls SHALL raise `NoVaultsConfiguredError`. |
| R-2.10 | WHEN migration runs and `~/.squirrel/state.json` exists, THE SYSTEM SHALL create `~/.squirrel/state/` if missing and move `state.json` to `~/.squirrel/state/<default-vault-name>.json`. |
| R-2.11 | THE SYSTEM SHALL be idempotent: running migration on an already-migrated file SHALL be a no-op (no rewrite, no comment duplication). |

## Unit 3: `lib/config_loader.py` API

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL expose a new module `lib/config_loader.py` with the public functions `list_vaults()`, `get_vault(name=None)`, `get_default_vault()`, `add_vault(name, path)`, `remove_vault(name)`, `set_default(name)`, `state_file_for(name)`, and `migrate_legacy()`. |
| R-3.2 | WHEN `list_vaults()` is called, THE SYSTEM SHALL return a list of `Vault` records in config-file order, each with `name`, `path` (resolved absolute Path), and `default` (bool). |
| R-3.3 | WHEN `get_vault(name)` is called with a name matching an entry, THE SYSTEM SHALL return that `Vault` record. |
| R-3.4 | IF `get_vault(name)` is called with a non-matching name, THE SYSTEM SHALL raise `VaultNotFoundError` containing the missing name and the list of valid names. |
| R-3.5 | WHEN `get_vault()` is called with no name, THE SYSTEM SHALL return the entry with `default = true`. |
| R-3.6 | WHEN `get_default_vault()` is called, THE SYSTEM SHALL return the entry with `default = true`. |
| R-3.7 | WHEN `add_vault(name, path)` is called, THE SYSTEM SHALL reject the call with a `ValidationError` if NAME already exists, if PATH does not exist on disk, or if PATH is not a directory. |
| R-3.8 | WHEN `add_vault(name, path)` is called with valid arguments, THE SYSTEM SHALL append a new vault entry with `default = false` and rewrite the config atomically. |
| R-3.9 | WHEN `remove_vault(name)` is called for the default vault, THE SYSTEM SHALL reject the call with a `ValidationError` requiring the caller to set another vault as default first. |
| R-3.10 | WHEN `remove_vault(name)` is called for a non-default vault, THE SYSTEM SHALL remove the entry and rewrite the config atomically. |
| R-3.11 | WHEN `set_default(name)` is called for an existing vault, THE SYSTEM SHALL clear `default = true` on every other vault and set it on the named vault. |
| R-3.12 | WHEN `set_default(name)` is called for a non-existent vault, THE SYSTEM SHALL raise `VaultNotFoundError`. |
| R-3.13 | WHEN `state_file_for(name)` is called, THE SYSTEM SHALL return the Path `~/.squirrel/state/<name>.json` with the parent directory created if missing. |
| R-3.14 | THE SYSTEM SHALL parse TOML using `tomllib` (Python 3.11+) when available, falling back to a hand-rolled parser for 3.9/3.10 that supports scalars, sections, and the `[[vaults]]` array-of-tables syntax. |

## Unit 4: `squirrel vaults` subcommand

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL provide a `squirrel vaults` subcommand group with `list`, `add`, `remove`, and `default` subcommands. |
| R-4.2 | WHEN `squirrel vaults list` runs, THE SYSTEM SHALL print one line per configured vault containing the name, the resolved absolute path, and a `(default)` marker for the default vault. |
| R-4.3 | WHEN `squirrel vaults add NAME PATH` runs, THE SYSTEM SHALL call `config_loader.add_vault(NAME, PATH)`; if it raises `ValidationError`, THE SYSTEM SHALL print the error and exit with code 1. |
| R-4.4 | WHEN `squirrel vaults remove NAME` runs, THE SYSTEM SHALL call `config_loader.remove_vault(NAME)`; if it raises `ValidationError`, THE SYSTEM SHALL print the error and exit with code 1. |
| R-4.5 | WHEN `squirrel vaults default NAME` runs, THE SYSTEM SHALL call `config_loader.set_default(NAME)`; if it raises, THE SYSTEM SHALL print the error and exit with code 1. |
| R-4.6 | WHEN any `squirrel vaults` subcommand succeeds, THE SYSTEM SHALL print a one-line confirmation to stdout. |
| R-4.7 | WHEN any `squirrel vaults` subcommand fails, THE SYSTEM SHALL print the error to stderr and exit with non-zero status. |

## Unit 5: `--vault NAME` on existing CLI subcommands

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL accept an optional `--vault NAME` argument on `squirrel status`. |
| R-5.2 | THE SYSTEM SHALL accept an optional `--vault NAME` argument on `squirrel deadlines`. |
| R-5.3 | THE SYSTEM SHALL accept an optional `--vault NAME` argument on `squirrel recover`. |
| R-5.4 | THE SYSTEM SHALL accept an optional `--vault NAME` argument on `squirrel dashboard`. |
| R-5.5 | WHEN any vault-touching subcommand runs without `--vault`, THE SYSTEM SHALL operate on the default vault as returned by `config_loader.get_default_vault()`. |
| R-5.6 | WHEN any vault-touching subcommand runs with `--vault NAME` for a non-existent vault, THE SYSTEM SHALL print a clear error naming the missing vault and the list of valid vaults, then exit with code 1. |
| R-5.7 | THE SYSTEM SHALL not change `squirrel chunk`, `squirrel estimate`, or `squirrel install`, which are vault-independent. |

## Unit 6: Slash commands

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | THE SYSTEM SHALL accept an optional `--vault NAME` token in `$ARGUMENTS` of every slash command that reads or writes a vault: `sq-status`, `sq-deadlines`, `sq-where-am-i`, `sq-start`, `sq-end`, `sq-capture`, `sq-brief`, `sq-decision`, `sq-recover`, `sq-chunk-intent`, `sq-task-initiation`, `sq-parakeet`, `sq-dashboard`, `sq-sync-out`, `sq-sync-in`. |
| R-6.2 | WHEN a slash command parses its arguments, THE SYSTEM SHALL extract `--vault NAME` if present and pass it as `--vault "$VAULT_NAME"` to every `python3 lib/...` invocation in the command's bash block. |
| R-6.3 | WHEN a slash command runs without `--vault`, THE SYSTEM SHALL omit the flag from script calls so each script defaults via `config_loader.get_default_vault()`. |
| R-6.4 | THE SYSTEM SHALL add a `--add-vault` flag to `/sq-init` that prompts for `name`, `path`, and `set-as-default? (y/n)` and writes a new entry to `~/.squirrel/config.toml`. |
| R-6.5 | THE SYSTEM SHALL not change `sq-chunk` or `sq-estimate`, which are vault-independent. |

## Unit 7: Skills

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | THE SYSTEM SHALL update the frontmatter of every `skills/*/SKILL.md` whose body invokes `lib/` scripts that touch the vault to document an optional `vault_name` argument. |
| R-7.2 | WHEN a skill receives a `vault_name` argument, THE SYSTEM SHALL pass `--vault $vault_name` to every `python3 lib/...` call in the skill body. |
| R-7.3 | WHEN a skill receives no `vault_name`, THE SYSTEM SHALL omit the flag, deferring to `config_loader.get_default_vault()`. |

## Unit 8: State files per vault

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | THE SYSTEM SHALL store per-vault state at `~/.squirrel/state/<vault-name>.json` rather than `~/.squirrel/state.json`. |
| R-8.2 | WHEN any code that previously read `~/.squirrel/state.json` runs after migration, THE SYSTEM SHALL read from `~/.squirrel/state/<vault-name>.json` for the active vault. |
| R-8.3 | WHEN any code writes per-vault state, THE SYSTEM SHALL write to `~/.squirrel/state/<vault-name>.json` atomically via temp file + `os.replace`. |
| R-8.4 | THE SYSTEM SHALL preserve the existing state schema (`current_project`, `current_intent`, `last_switch_at`, `switch_ledger`) per file unchanged. |

## Unit 9: Backward compatibility & regression

| ID    | EARS statement |
|-------|----------------|
| R-9.1 | THE SYSTEM SHALL produce byte-identical CLI and slash command output for single-vault users post-migration, given the same inputs. |
| R-9.2 | THE SYSTEM SHALL keep all existing tests in `tests/` passing without modification. |
| R-9.3 | IF a user reverts to a legacy `config.toml` after migration (e.g., restores from backup with no `[[vaults]]`), THE SYSTEM SHALL run migration again on next load. |
| R-9.4 | THE SYSTEM SHALL not require any user to manually run a migration command. |
| R-9.5 | WHILE migration is running, THE SYSTEM SHALL not produce output to stderr (it is a silent transparent rewrite). The single observable artifact is the `# Auto-migrated <ISO-date>` comment in the rewritten file. |

## Unit 10: Documentation

| ID    | EARS statement |
|-------|----------------|
| R-10.1 | THE SYSTEM SHALL document the new `[[vaults]]` schema in `INSTALL.md`. |
| R-10.2 | THE SYSTEM SHALL add a "Multiple vaults" section to `docs/guides/getting-started.md` covering: when to use multiple vaults, `squirrel vaults add/list/remove/default`, and `--vault NAME` on slash commands. |
| R-10.3 | THE SYSTEM SHALL document the migration behavior (lazy, idempotent, the comment marker) in both files above. |
