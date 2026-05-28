# Multi-Vault Core — Tasks

> Source: `docs/hld/multi-vault-core.md`, `docs/lld/multi-vault-core.md`, `docs/ears/multi-vault-core.md`.
> Arrow of intent: HLD → LLD → EARS → these tasks → code/tests.

## Conventions

- Story IDs are stable; never renumber. Use `(deps: X.Y)` for inside-this-file dependencies.
- `(mutex: tag)` marks stories that touch the same file or schema; they cannot run concurrently with each other.
- Acceptance line references an R-X.Y in `docs/ears/multi-vault-core.md`. If a story covers multiple Rs, list them.
- Verify line is the exact observable check that confirms the requirement is met — runnable command, file inspection, or test name.
- Private technical breakdown (sketches, prototypes, scratch notes) goes in `.devlocal/<user>/<story-id>/scratchpad.md`. Do not put it here.

## Dependency overview

```
   1.1 schema template
       │
       ▼
   1.2 config_loader (read)──┐
       │                     │
       ▼                     ▼
   1.3 config_loader (write) 1.4 migration ──► 5.3 robustness
       │                     │
       ▼                     ▼
   2.1 vaults list           1.5 per-vault state
   2.2 vaults add                │
   2.3 vaults remove/default     ▼
       │                     2.4 --vault on CLI
       ▼                         │
   3.2 /sq-init --add-vault      ▼
                             3.1 slash commands --vault
                                 │
                                 ▼
                             4.1 skills forward vault_name
                                 │
                                 ▼
                             5.1 existing tests still pass
                             5.2 regression: byte-identical output
                                 │
                                 ▼
                             6.1 INSTALL.md
                             6.2 getting-started.md
```

---

## Unit 1 — Config schema, config_loader, migration

- [x] 1.1 **Define new config schema + update template** (est: ~30m, mutex: config_toml)
  - acceptance: R-1.1, R-1.2, R-1.4, R-1.6, R-1.7
  - verify: `config/squirrel.toml.example` contains `[[vaults]]` block with `name`, `path`, `default = true` on the first entry; rename `environment_name` → `machine_environment` in the template; tilde expansion documented inline.

- [x] 1.2 **Implement `lib/config_loader.py` read API** (deps: 1.1, est: ~2h, mutex: config_loader)
  - acceptance: R-3.1, R-3.2, R-3.3, R-3.4, R-3.5, R-3.6, R-3.13, R-3.14
  - verify: `tests/test_config_loader.py` covers `list_vaults`, `get_vault(name)`, `get_vault()`, `get_default_vault`, `state_file_for`. Tests pass under Python 3.9, 3.11, 3.12. TOML parser fallback exercised by mocking `tomllib` import on 3.11.

- [x] 1.3 **Implement `lib/config_loader.py` write API** (deps: 1.2, est: ~2h, mutex: config_loader)
  - acceptance: R-3.7, R-3.8, R-3.9, R-3.10, R-3.11, R-3.12
  - verify: `tests/test_config_loader.py` covers `add_vault` (happy path, duplicate-name, missing-path, non-directory), `remove_vault` (happy path, default-refuse), `set_default` (happy path, missing-name). Atomic writes verified via temp-file inspection.

- [x] 1.4 **Implement migration from legacy config** (deps: 1.2, est: ~3h, mutex: config_loader)
  - acceptance: R-1.3, R-1.5, R-2.1, R-2.2, R-2.3, R-2.4, R-2.5, R-2.6, R-2.7, R-2.8, R-2.9, R-2.10, R-2.11
  - verify: `tests/test_config_loader.py::test_migration_*` — given a legacy file with `vault_path` + `environment_name` + a `[compliance]` section + comments, the migration produces a file with `[[vaults]]`, `machine_environment`, the `# Auto-migrated` comment as line 1, and every other line preserved. Running migration twice is a no-op. Reverting to legacy and re-loading re-migrates. State file move tested with a fixture vault state.

- [x] 1.5 **Per-vault state files** (deps: 1.2, 1.4, est: ~1.5h, mutex: state_files)
  - acceptance: R-8.1, R-8.2, R-8.3, R-8.4
  - verify: `lib/session_scanner.py` and `lib/switch_tracker.py` read/write `~/.squirrel/state/<vault>.json`. New test `tests/test_per_vault_state.py` writes state for two vaults concurrently and confirms no collision. Existing schema (`current_project`, `current_intent`, `last_switch_at`, `switch_ledger`) preserved.

---

## Unit 2 — `squirrel vaults` subcommand + `--vault` on CLI

- [x] 2.1 **`squirrel vaults list`** (deps: 1.3, est: ~30m, mutex: squirrel_cli)
  - acceptance: R-4.1 (list portion), R-4.2, R-4.6
  - verify: run `squirrel vaults list` on a two-vault config; stdout shows one line per vault with `(default)` marker on the right one. Exit code 0.

- [x] 2.2 **`squirrel vaults add NAME PATH`** (deps: 1.3, est: ~45m, mutex: squirrel_cli)
  - acceptance: R-4.1 (add portion), R-4.3, R-4.6, R-4.7
  - verify: `squirrel vaults add work /tmp/test-vault` appends entry; bad path errors with exit code 1; duplicate name errors with exit code 1. Config file inspected after each.

- [x] 2.3 **`squirrel vaults remove` and `default`** (deps: 1.3, est: ~45m, mutex: squirrel_cli)
  - acceptance: R-4.1 (remove + default portions), R-4.4, R-4.5, R-4.6, R-4.7
  - verify: `squirrel vaults default work`, then `squirrel vaults remove personal` succeeds; `squirrel vaults remove work` now refuses with exit code 1; messages contain the offending name and remediation hint.

- [x] 2.4 **Add `--vault NAME` to existing CLI subcommands** (deps: 1.5, est: ~1.5h, mutex: squirrel_cli)
  - acceptance: R-5.1, R-5.2, R-5.3, R-5.4, R-5.5, R-5.6, R-5.7
  - verify: `squirrel status --vault work` returns work's status; `squirrel status` returns default's; `squirrel status --vault missing` exits 1 with clear error. Same for `deadlines`, `recover`, `dashboard`. `chunk`, `estimate`, `install` unchanged — verified by running them and confirming no new flag in `--help`.

---

## Unit 3 — Slash commands

- [x] 3.1 **Add `--vault NAME` to vault-touching slash commands** (deps: 2.4, est: ~3h, mutex: slash_commands)
  - acceptance: R-6.1, R-6.2, R-6.3, R-6.5
  - verify: each of the 15 listed `.md` files in `commands/` (status, deadlines, where-am-i, start, end, capture, brief, decision, recover, chunk-intent, task-initiation, parakeet, dashboard, sync-out, sync-in) has an argument-parsing block extracting `--vault NAME` and forwarding it as `--vault "$VAULT_NAME"` to every `python3 lib/...` call. `chunk` and `estimate` unchanged.

- [x] 3.2 **`/sq-init --add-vault` subflow** (deps: 2.2, est: ~1.5h, mutex: slash_commands)
  - acceptance: R-6.4
  - verify: invoking `/sq-init --add-vault` prompts for name, path, set-as-default (y/n) and appends to `config.toml`. Existing `/sq-init` (no flag) behavior unchanged for first-time users.

---

## Unit 4 — Skills

- [x] 4.1 **Skills forward `vault_name`** (deps: 3.1, est: ~2h, mutex: skills)
  - acceptance: R-7.1, R-7.2, R-7.3
  - verify: every `skills/*/SKILL.md` whose body invokes a vault-touching `lib/*.py` script declares `vault_name` as an optional argument in its frontmatter description and forwards `--vault $vault_name` when present. Audit list: capture, brief, decision, session-start, session-end, sync-in, sync-out, where-am-i, recover, parakeet, chunk-intent, task-initiation. (Skills like `hyperfocus-guardian` audited separately and noted as vault-touching or not.)
  - audit outcome: script-vault skills (brief, parakeet, recover, session-start, where-am-i) replaced legacy `vault_path` lookup with `config_loader.get_vault(name=vault_name)` so the resolved path flows to lib scripts (R-7.2). Read/write-vault skills (capture, decision, session-end, sync-in, sync-out, task-initiation) document `vault_name` in frontmatter for scoping their file writes (R-7.1). `chunk-intent` is vault-independent (only invokes chunk_helper/estimate_buffer per R-5.7) → no change. `hyperfocus-guardian` reads `~/.squirrel/state.json` directly but does not invoke any vault-touching lib script → no change required for R-7.1.

---

## Unit 5 — Regression & robustness

- [x] 5.1 **All existing tests pass unchanged** (deps: 1.4, 1.5, 2.4, est: ~1h)
  - acceptance: R-9.2
  - verify: `python3 -m unittest discover tests` from repo root exits 0; the test count is at least the pre-change count. Every fixture in `tests/fixtures/` is untouched.

- [x] 5.2 **Single-vault user sees byte-identical CLI output** (deps: 5.1, est: ~1h)
  - acceptance: R-9.1
  - verify: with a single-vault `config.toml` (post-migration), capture stdout of `squirrel status` and `squirrel deadlines` to a fixture file. Diff against the pre-change captured output: zero diff lines. New test `tests/test_regression_single_vault.py` runs both commands and asserts against the captured fixture.

- [x] 5.3 **Re-migration robustness** (deps: 1.4, est: ~45m)
  - acceptance: R-9.3, R-9.4, R-9.5
  - verify: take a migrated config, manually overwrite it with the legacy form (`vault_path = ...`), load via any CLI command, observe that `[[vaults]]` is rebuilt and the `# Auto-migrated` comment is present. No stderr output during migration.

---

## Unit 6 — Documentation

- [x] 6.1 **Update INSTALL.md** (deps: 1.4, 2.3, est: ~45m, mutex: docs)
  - acceptance: R-10.1, R-10.3
  - verify: `INSTALL.md` contains an example of the new `[[vaults]]` schema, the `# Auto-migrated` migration behavior, and a one-liner about `squirrel vaults add/list/remove/default`.

- [x] 6.2 **Add "Multiple vaults" to user guide** (deps: 3.2, est: ~1h, mutex: docs)
  - acceptance: R-10.2, R-10.3
  - verify: `docs/guides/getting-started.md` has a new section between "First Setup" and "Everyday Use" titled "Working with multiple workspaces" covering: when to use multiple, `squirrel vaults` commands, `--vault NAME` on slash commands, and that migration is automatic for existing users.

---

## Estimates & critical path

| Phase | Stories | Wall-clock estimate |
|---|---|---|
| Foundation (Unit 1) | 1.1, 1.2, 1.3, 1.4, 1.5 | ~9h |
| CLI surface (Unit 2) | 2.1, 2.2, 2.3, 2.4 | ~3.5h |
| Slash commands (Unit 3) | 3.1, 3.2 | ~4.5h |
| Skills (Unit 4) | 4.1 | ~2h |
| Regression (Unit 5) | 5.1, 5.2, 5.3 | ~2.75h |
| Documentation (Unit 6) | 6.1, 6.2 | ~1.75h |
| **Total** | **15 stories** | **~23.5h** (one developer, focused) |

Realistic calendar at half-time: **5–7 days**. Critical path runs through Unit 1 (cannot parallelize the lib/config_loader work).

## Parallelization opportunities

- After 1.3 lands: 2.1, 2.2, 2.3 can run in parallel (different CLI handler files; same mutex tag handles serialization at code-merge time).
- After 2.4 lands: 3.1 and 6.1 can run in parallel.
- 6.2 can start as soon as 3.2 is done.
- 5.1, 5.2, 5.3 can run in parallel (different test files).
