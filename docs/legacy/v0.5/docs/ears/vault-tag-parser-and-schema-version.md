# Vault Tag Parser & Contract Versioning — EARS Specifications

## Unit 1: Tag schema validation (VAULT-003)

| ID | EARS statement |
|----|----------------|
| R-1.1 | THE SYSTEM SHALL validate tags against the pattern `^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-\d{3}$`; any tag not matching this pattern SHALL be considered invalid. |
| R-1.2 | WHEN a tag fails validation, THE SYSTEM SHALL return both a human-readable rejection reason and a suggested corrected form. |
| R-1.3 | `lib/tag_parser.py` SHALL be the sole module implementing tag pattern matching; no other file in `lib/` or `skills/` SHALL contain a tag validation regex. |
| R-1.4 | WHEN a tag's numeric suffix is present but fewer than 3 digits, THE SYSTEM SHALL suggest the zero-padded 3-digit form (e.g. `VISA-FAMILIA-TRAMITE-1` → `VISA-FAMILIA-TRAMITE-001`). |
| R-1.5 | WHEN a tag contains any lowercase letter, THE SYSTEM SHALL suggest the fully uppercased equivalent before applying other corrections. |
| R-1.6 | IF a tag has fewer than 3 named segments before the numeric suffix (e.g. `VISA-001`), THE SYSTEM SHALL reject it as structurally invalid and SHALL NOT produce a numeric-only correction. |
| R-1.7 | WHEN `validate()` is called with `None` or an empty string, THE SYSTEM SHALL return `(False, None)`; no suggestion is produced for absent input. |
| R-1.8 | `lib/tag_parser.py` SHALL expose a `__main__` entry point; WHEN invoked as `python3 lib/tag_parser.py <tag>`, THE SYSTEM SHALL print the validation result and exit with code `0` if valid or `1` if invalid. |
| R-1.9 | THE SYSTEM SHALL implement tag_parser using Python stdlib only; no third-party packages SHALL be imported. |

## Unit 2: Aggregator contract versioning (VAULT-005)

| ID | EARS statement |
|----|----------------|
| R-2.1 | THE SYSTEM SHALL include a `schema_version` field in all JSON output emitted by `lib/status_aggregator.py`. |
| R-2.2 | The initial value of `schema_version` SHALL be the string `"001"` (zero-padded, not an integer). |
| R-2.3 | `schema_version` SHALL be the first key in the top-level JSON object in all output modes (`--json`, `--pretty`, `--detailed`). |
| R-2.4 | WHEN the top-level JSON shape changes in a backwards-incompatible way (key removed, type changed, key renamed), THE SYSTEM SHALL increment `schema_version` before the change ships. |
| R-2.5 | Adding a new optional key to the JSON output SHALL NOT require a `schema_version` bump. |
