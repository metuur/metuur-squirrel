# Vault Tag Parser & Contract Versioning — Tasks

> EARS: docs/ears/vault-tag-parser-and-schema-version.md
> LLD:  docs/lld/vault-tag-parser-and-schema-version.md
> Status: `[ ]` open · `[~]` in progress · `[x]` done

---

## Unit 1: Tag schema validation (VAULT-003)

- [x] 1.1 Create `lib/tag_parser.py` (est: ~45m)
  - acceptance: R-1.1 — validate() returns (True, None) for `^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-\d{3}$`; (False, suggestion) otherwise
  - acceptance: R-1.3 — this is the sole file containing tag validation regex
  - acceptance: R-1.4 — `VISA-FAMILIA-TRAMITE-1` → suggestion `VISA-FAMILIA-TRAMITE-001`
  - acceptance: R-1.5 — `visa-familia-tramite-001` → suggestion `VISA-FAMILIA-TRAMITE-001`
  - acceptance: R-1.6 — `VISA-001` → (False, None) with structural rejection; no numeric-only correction
  - acceptance: R-1.7 — `validate(None)` and `validate("")` → (False, None)
  - acceptance: R-1.8 — `python3 lib/tag_parser.py VISA-FAMILIA-TRAMITE-001` exits 0; invalid tag exits 1
  - acceptance: R-1.9 — no import outside Python stdlib
  - verify: `python3 lib/tag_parser.py VISA-001` prints invalid + structural error, exits 1
  - verify: `python3 lib/tag_parser.py visa-familia-tramite-1` prints suggestion `VISA-FAMILIA-TRAMITE-001`, exits 1
  - verify: `python3 lib/tag_parser.py VISA-FAMILIA-TRAMITE-001` prints valid, exits 0

- [x] 1.2 Tests for tag_parser in `tests/test_foundation.py` (deps: 1.1, est: ~30m)
  - acceptance: R-1.1 — test valid tag returns (True, None)
  - acceptance: R-1.4 — test un-padded suffix returns correct suggestion
  - acceptance: R-1.5 — test lowercase tag returns uppercased suggestion
  - acceptance: R-1.6 — test 2-segment tag returns (False, None); structural rejection
  - acceptance: R-1.7 — test None and "" both return (False, None)
  - acceptance: R-1.8 — test CLI exits 0 for valid, 1 for invalid (subprocess call)
  - verify: `python3 -m pytest tests/ -q` — all existing 68 + new tag_parser tests pass

---

## Unit 2: Aggregator contract versioning (VAULT-005)

- [x] 2.1 Add `schema_version: "001"` to `aggregate_status()` return dict (est: ~15m)
  - acceptance: R-2.1 — `schema_version` key present in output of `aggregate_status()`
  - acceptance: R-2.2 — value is the string `"001"`, not integer 1
  - acceptance: R-2.3 — `schema_version` is the first key in the returned dict (and thus first in `--json` output)
  - verify: `python3 lib/status_aggregator.py --vault tests/fixtures/vault-minimal | python3 -c "import json,sys; d=json.load(sys.stdin); assert list(d)[0]=='schema_version'; assert d['schema_version']=='001'"`

- [x] 2.2 Tests for schema_version in `tests/test_foundation.py` (deps: 2.1, est: ~15m)
  - acceptance: R-2.1 — assert `"schema_version"` in output dict
  - acceptance: R-2.2 — assert `output["schema_version"] == "001"`
  - acceptance: R-2.3 — assert `list(output.keys())[0] == "schema_version"`
  - verify: `python3 -m pytest tests/ -q` — all tests pass including new schema_version assertions
