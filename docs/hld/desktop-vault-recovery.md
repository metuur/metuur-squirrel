# Desktop Vault Recovery — High-Level Design

> _Backfilled from the as-built `apps/desktop/src/components/VaultRecovery.tsx`,
> `VaultRecoveryGate.tsx`, and the backend `_vault_setup_error` /
> `classify_vault` path in `apps/backend/server.py`._

## Overview

`in-app-vault-onboarding` handles the **first-run** case: a brand-new user with no
configured vault. But a configured vault can become **unusable later** — the user
moves the folder, empties it, or points Squirrel at a raw Obsidian vault that was
never structured. Before this change, that surfaced in the desktop popup as a
generic "Backend offline"-style failure with no path forward.

This change adds a **blocking recovery overlay** in the desktop popup that detects
the specific failure from the `/api/me` error payload and guides the user to the
right fix **in-app**, without opening the web UI: re-pick/create a folder, generate
the Squirrel structure into an empty folder, or convert an unstructured folder via
`/sq-migrate-vault`. It is the returning-user counterpart to onboarding.

## Stakeholders & Impact

- **Returning user whose vault broke:** instead of a dead popup, gets a titled,
  guided overlay matched to the exact problem (missing / empty / unstructured) and
  recovers in one or two clicks.
- **Desktop popup:** gains a gate that takes over the whole surface when the
  configured vault is unusable, yielding to the offline/handshake banners for
  transport-level errors.
- **Backend `/api/me`:** already classifies the vault; this feature consumes its
  structured `409` error codes rather than treating them as generic failures.
- **Migration engine:** the `VAULT_UNSTRUCTURED` path is the in-popup on-ramp to
  `/sq-migrate-vault` (see `docs/hld/obsidian-vault-migration-skill.md`).

## Goals

- Detect a configured-but-unusable vault from `/api/me` and present a guided,
  blocking recovery overlay in the popup.
- Cover three distinct failures with three distinct flows: not-found, empty,
  unstructured.
- Complete recovery actions **in-app** (consistent with the rest of the popup),
  with an escape hatch to the larger web UI window.
- Re-probe after each action and return to the normal popup once the vault is
  healthy.
- Distinguish vault-recovery errors from transport/auth/offline errors so the
  correct banner owns the screen.

## Non-Goals

- No change to the first-run onboarding wizard (`OnboardingGate`); this gate fires
  independently on vault health, not on the first-run "done" flag.
- No in-popup file-tree browser; folder selection uses the native OS dialog.
- No migration logic in the popup — the unstructured flow hands off to
  `/sq-migrate-vault`, run in the user's coding agent.
- No recovery for transport-level failures (offline / 401) — those remain owned by
  `BackendStatusBanner` / `HandshakeBanner`.

## Success Criteria

1. **Missing folder:** with the configured vault folder moved/deleted, opening the
   popup shows "Workspace not found", lets the user pick or type a folder, and
   (re)creates it; the popup then reloads against the healthy vault.
2. **Empty folder:** a configured but empty folder shows "Your workspace is empty"
   with a one-click "Generate structure" that scaffolds the Squirrel layout.
3. **Unstructured folder:** a folder with non-Squirrel notes shows "Convert your
   existing vault" with a create-new-vault step and a copy-able `/sq-migrate-vault`
   command; the original folder is never modified.
4. **Yielding:** when the backend is offline or the token is unaccepted, the
   recovery gate stays out of the way and the offline/handshake banner shows.
5. **Self-clearing:** after a successful action, a re-probe of `/api/me` succeeds
   and the popup returns to normal without a manual restart.
