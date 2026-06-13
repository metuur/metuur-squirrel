# Desktop Vault Recovery — EARS Specifications

> _Backfilled from the as-built popup recovery gate and backend classifier._

## Unit 1: Backend vault classification

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL classify a configured vault path as one of `ok`, `missing`, `empty`, or `unstructured`. |
| R-1.2 | WHEN the configured vault is not `ok`, THE `/api/me` endpoint SHALL respond `409` with a machine-readable `code` and `details` carrying the vault name and path. |
| R-1.3 | WHEN the vault classifies as `unstructured`, THE SYSTEM SHALL include a ready-to-run `migrate_command` of the form `/sq-migrate-vault <path>` in the error details. |
| R-1.4 | THE SYSTEM SHALL use the codes `NO_VAULT`, `VAULT_MISSING`, `VAULT_EMPTY`, and `VAULT_UNSTRUCTURED` for the no-vault, missing, empty, and unstructured cases respectively. |

## Unit 2: Recovery gate detection & yielding

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the desktop popup mounts, THE SYSTEM SHALL probe `/api/me` and, if it succeeds, render no recovery overlay. |
| R-2.2 | WHEN `/api/me` fails with a vault-recovery code, THE SYSTEM SHALL render a blocking, modal recovery overlay over the popup. |
| R-2.3 | WHEN `/api/me` fails with a transport, offline, or `401` error (not a vault-recovery code), THE SYSTEM SHALL NOT render the recovery overlay, yielding to the backend-offline / handshake banners. |

## Unit 3: Recovery flows

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN the code is `NO_VAULT` or `VAULT_MISSING`, THE SYSTEM SHALL present a path input (prefilled with the current path) and a native folder picker, and on confirm call `POST /api/config/vault` with `create: true`. |
| R-3.2 | WHEN the code is `VAULT_EMPTY`, THE SYSTEM SHALL present a single action that generates the Squirrel starter structure into the existing folder via `POST /api/config/vault` with `create: true`. |
| R-3.3 | WHEN the code is `VAULT_UNSTRUCTURED`, THE SYSTEM SHALL present a two-step flow: create a new destination vault (required to differ from the source folder) and show a copy-able `/sq-migrate-vault` command. |
| R-3.4 | THE SYSTEM SHALL complete all recovery actions in-app within the popup, and SHALL NOT modify the source folder in the unstructured flow. |
| R-3.5 | THE SYSTEM SHALL offer an escape-hatch link to complete setup in the larger web UI window. |
| R-3.6 | THE SYSTEM SHALL select folders via the native OS directory dialog and SHALL NOT use `window.prompt`/`confirm`. |

## Unit 4: Re-probe & exit

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN the user completes a recovery action, THE SYSTEM SHALL re-probe `/api/me`. |
| R-4.2 | WHEN the re-probe succeeds, THE SYSTEM SHALL reload the popup so every widget re-initializes against the recovered vault. |
| R-4.3 | WHEN the re-probe still returns a recovery code, THE SYSTEM SHALL update the overlay to the new recovery state rather than dismissing it. |

## Unit 5: Backend write contract

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | WHEN `POST /api/config/vault` is called with `create: true` and the path does not exist, THE SYSTEM SHALL create the folder before persisting. |
| R-5.2 | THE SYSTEM SHALL validate the vault name and path before any filesystem write and reject invalid input with `400`. |
| R-5.3 | WHEN the target folder classifies as `unstructured`, THE SYSTEM SHALL persist the vault config WITHOUT scaffolding the Squirrel skeleton, leaving the folder intact for migration. |
| R-5.4 | WHEN the target folder is empty or already Squirrel-structured, THE SYSTEM SHALL scaffold the skeleton and mind journal idempotently, treating scaffolding failures as non-fatal. |
