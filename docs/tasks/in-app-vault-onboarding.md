# In-App Vault Onboarding — Tasks

Source specs: `docs/hld/in-app-vault-onboarding.md`, `docs/lld/in-app-vault-onboarding.md`, `docs/ears/in-app-vault-onboarding.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Dependency layers:
```
1.1  config_loader: upsert_default_vault + TOML-safe escaping   (foundation)
 │
 ├─ 3.1  POST /api/config/vault  (validation + persist)
 │
2.1  GET /api/env/obsidian       (independent backend)
 │
 ├─ 4.1  typed client: getObsidianStatus + setVaultConfig  ──► 4.2 OnboardingWizard ──► 4.3 App.tsx first-run gate
 │
1.4  add tauri-plugin-dialog dep + capability  ─────────────────► 4.2

5.1  OpenVaultButton un-hardcode (tolerate 503)   (independent)
5.2  tray.rs un-hardcode (tolerate no-vault)      (independent)
```

## Unit 1: Backend foundation — config write contract

- [x] **1.1** Add `upsert_default_vault(name, path)` to `apps/cli/lib/config_loader.py` + make `_format_vault_entry` emit TOML-safe quoted strings (est: ~75m)
  - acceptance:
    - R-3.10 — Appends/updates the vault and marks it the **sole** `default = true`; on any failure leaves `config.toml` unchanged (single atomic write, not add+set_default's two writes).
    - R-3.11 — If a vault with `name` already exists, update its `path` and mark default (idempotent upsert) instead of raising duplicate-name (`add_vault:614-615`).
    - R-3.8 — Preserves `default_email`, `machine_environment`, and all other vault entries byte-intact except the added/updated entry and the relocated `default` flag.
    - R-3.13 (partial) — `_format_vault_entry` quotes/escapes `name`/`path` so a value with `"`/newline cannot corrupt the file (fixes raw f-string at `config_loader.py:562-570`).
  - verify:
    - pytest: seed config with `default_email`, `machine_environment`, vault `personal`(default) + `work`. Call `upsert_default_vault("personal", "/tmp/v")` → `personal.path` updated, `personal` is sole default, `work` + scalar keys unchanged.
    - pytest: `upsert_default_vault("new", "/tmp/n")` on that config → `new` appended as sole default, `personal`/`work` now `default=false`.
    - pytest: round-trip — config with a comment line; upsert; assert non-target lines byte-identical.
    - pytest: simulate write failure mid-call → original file intact.

- [x] **1.4** Add `tauri-plugin-dialog` dependency + capability grant (est: ~30m)
  - acceptance:
    - R-3.1 (prereq) — `apps/desktop/src-tauri/Cargo.toml` gains `tauri-plugin-dialog = "2"`, plugin initialized in `lib.rs`, and `capabilities/default.json` grants the exact dialog-open permission identifier for the installed v2 plugin (confirm id; wrong id reproduces the silent-denial bug from the opener learn).
  - verify:
    - `cargo build` for `src-tauri` succeeds.
    - Temporary frontend call to `open({ directory: true })` opens a native folder dialog (manual smoke); remove the smoke call after confirming.

## Unit 2: Obsidian detection

- [x] **2.1** Add `GET /api/env/obsidian` to `apps/backend/server.py` (est: ~45m)
  - acceptance:
    - R-2.1 / R-2.2 — Returns `{ installed, path }`; installed if `/Applications/Obsidian.app` exists, else if `mdfind "kMDItemCFBundleIdentifier == 'md.obsidian'"` finds a bundle.
    - R-2.3 — Detected → `{ installed: true, path: <app path> }`.
    - R-2.4 — Not detected → `{ installed: false, path: null }`.
    - R-2.8 — `mdfind` is bounded by a timeout; on timeout/Spotlight-unavailable return `installed: false`.
  - verify:
    - Manual: `curl -H 'X-Squirrel-Token: …' 127.0.0.1:3939/api/env/obsidian` on a machine with Obsidian → `installed:true` + real path.
    - pytest with `/Applications/Obsidian.app` path monkeypatched present/absent → both branches; `mdfind` stubbed to hang → returns `installed:false` within timeout.

## Unit 3: Vault persistence endpoint

- [x] **3.1** Add `POST /api/config/vault` to `apps/backend/server.py` (deps: 1.1, est: ~75m)
  - acceptance:
    - R-3.3 / R-3.6 / R-3.7 — Body `{ name?, path, create? }`; `name` defaults to `personal`; persists via `upsert_default_vault`, expanding `~`.
    - R-3.4 — Handler order: validate name → validate/expand path → `mkdir -p` if `create` → assert is-dir → persist.
    - R-3.5 — Path not a directory after create → 400, no config change.
    - R-3.12 — Reject path that (after `~`/symlink expansion) is not absolute or escapes `$HOME`, 400, no `mkdir`.
    - R-3.13 — Reject `name` not matching `[A-Za-z0-9._-]+`, 400, before any write.
    - R-3.10 — On write failure → 500, `config.toml` unchanged.
    - Error contract: 200 `{name, path, default:true}` / 400 / 401 (token gate) / 500 per LLD table.
  - verify:
    - pytest: valid body with `create:true` on a non-existent in-`$HOME` path → 200, folder created, config has it as sole default.
    - pytest: path traversal `../../etc` and absolute `/tmp/x` outside `$HOME` → 400, nothing created.
    - pytest: `name:"a b"` / `name:'x";evil'` → 400, no write.
    - pytest: re-POST same `personal` body twice → idempotent (200 both, one default).
    - pytest: missing token → 401.

## Unit 4: Onboarding wizard + first-run gate

- [x] **4.1** Add `getObsidianStatus()` + `setVaultConfig()` to `apps/desktop/src/api/client.ts` (deps: 2.1, 3.1, est: ~30m)
  - acceptance:
    - R-2.1 — `getObsidianStatus()` → `GET /api/env/obsidian`, typed `{ installed, path }`.
    - R-3.3 — `setVaultConfig({ name?, path, create? })` → `POST /api/config/vault`; surfaces 400/500 as typed errors.
  - verify: typecheck passes; unit test mocks fetch and asserts URL/method/body + error mapping for 400.

- [x] **4.2** Create `apps/desktop/src/components/OnboardingWizard.tsx` (deps: 1.4, 4.1, est: ~120m)
  - acceptance:
    - R-2.1/2.3/2.4/2.5/2.6/2.7 — Obsidian step: shows found path; if not found shows download link to `https://obsidian.md/download` (via `openUrl`, https already allowed), "Re-check" re-calls status, and a "Skip"/continue control; user may always proceed.
    - R-3.1/3.2 — Vault step: "Use existing folder" opens native picker (`open({directory:true})`); "Create new" presents editable `~/squirrel-vault`.
    - R-3.3/3.9 — Confirm calls `setVaultConfig`; on backend error/unreachable, stay on vault step with message.
    - R-1.4 — Final step sets store key `onboarding.done = true` and dismisses.
  - verify:
    - Component test (mocked api + dialog): not-installed branch renders download link + re-check; vault confirm success advances to done and sets the flag; backend 400 keeps user on vault step with error.
    - Manual smoke in the running app: full happy path welcome→done.

- [x] **4.3** Wire first-run gate into `apps/desktop/src/App.tsx` (deps: 4.2, est: ~45m)
  - acceptance:
    - R-1.1 — On mount, if store `onboarding.done` absent/false → render `<OnboardingWizard/>` as blocking full-screen overlay (HandshakeBanner pattern).
    - R-1.2 — Flag true → normal UI, no wizard.
    - R-1.3 — If handshake banner active, it takes precedence (wizard overlay does not mount until handshake clears).
    - R-1.6 — If the flag can't be read, treat as not-done (show wizard).
    - R-1.5 — No installer responsibilities (binaries/launchd/agent-pack) touched.
  - verify:
    - Component test: store unset → wizard shown; store `done:true` → wizard absent; handshake-active + store-unset → handshake shown, wizard not mounted; store read throws → wizard shown.
    - Manual: complete wizard, relaunch app → goes straight to normal UI.

## Unit 5: Vault wiring (un-hardcode)

- [x] **5.1** `OpenVaultButton.tsx` uses configured vault name, tolerant of 503 (est: ~40m)
  - acceptance:
    - R-4.1 — Opens `obsidian://open?vault=<active vault name from /api/me>`, not hardcoded `vault-tdah` (`OpenVaultButton.tsx:3`).
    - R-4.3 — No vault name available → action omitted/disabled.
    - R-4.4 — `/api/me` 503/empty (no vault yet) → treated as disabled, no crash.
  - verify:
    - Component test: `/api/me` returns vault `mine` → opens `obsidian://open?vault=mine`; `/api/me` 503 → button disabled/absent, no throw.

- [x] **5.2** `tray.rs` uses configured vault name, tolerant of no-vault at build (est: ~50m)
  - acceptance:
    - R-4.2 — Tray "Open Vault" uses configured vault name, not `OBSIDIAN_VAULT = "vault-tdah"` (`tray.rs:36`).
    - R-4.4 — Tray builds successfully when no vault is configured (no panic/block at app start); Open Vault disabled/omitted in that state.
  - verify:
    - `cargo build` + existing `tray_icons` test still passes.
    - Manual: with no configured vault, app launches and tray builds; after onboarding, tray "Open Vault" opens the chosen vault.
