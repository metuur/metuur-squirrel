# Vault Tag Parser & Contract Versioning — Low-Level Design

## Architecture

### lib/tag_parser.py

Single module, stdlib-only. Three public functions + `__main__` entry point.

```
tag_parser.py
├── validate(tag: str) -> tuple[bool, str | None]
│     Returns (True, None) if valid.
│     Returns (False, suggestion: str) if invalid.
│
├── normalize(tag: str) -> str
│     Uppercase all segments. Zero-pad numeric suffix to 3 digits.
│     Does not validate — call validate() first.
│
├── parse(tag: str) -> dict | None
│     Returns {"proyecto": str, "subarea": str, "componente": str, "n": int}
│     Returns None if tag does not match the 4-part schema.
│
└── __main__
      python3 lib/tag_parser.py <tag>
      Prints: "✅ Valid" or "❌ Invalid — suggestion: <suggestion>"
      Exit 0 if valid, exit 1 if invalid.
```

**Tag schema** (`PROYECTO-SUBÁREA-COMPONENTE-NNN`):
- Exactly 4 dash-separated segments.
- Segments 1–3: one or more uppercase ASCII letters/digits (`[A-Z][A-Z0-9]*`).
- Segment 4: numeric suffix, exactly 3 zero-padded digits (`\d{3}`).
- Total regex: `^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-\d{3}$`

**Suggestion logic** (applied in order):
1. Uppercase all characters.
2. Replace spaces and underscores with `-`.
3. If numeric suffix present but not 3-digit: zero-pad (e.g. `1` → `001`).
4. If fewer than 4 segments: append `-MISC-001` to the shortest plausible form.
5. Strip non-ASCII characters.

**None / empty input**: `validate(None)` and `validate("")` return `(False, None)` — no suggestion, tag is absent.

### lib/status_aggregator.py — schema_version addition

Add `schema_version: "001"` as the **first key** of the top-level dict returned by `_build_output()`. This key is present in all output modes (`--json`, `--pretty`, `--detailed`).

```python
output = {
    "schema_version": "001",
    # ... existing keys unchanged ...
}
```

No other changes to the JSON shape. No callers need updating — `schema_version` is additive.

## Constraints

- Python stdlib only (`re`, `sys`). No PyYAML, no third-party packages (VAULT-008).
- `tag_parser.py` must be importable by `status_aggregator.py`, `intent_parser.py`, and any future skill without circular imports.
- `__main__` block must exit 0/1 (usable in shell scripts and pre-commit hooks).

## Key Decisions

- **4 segments, not 3**: the schema is `PROYECTO-SUBÁREA-COMPONENTE-NNN` — the numeric suffix is mandatory and separate. `VISA-001` has only 2 named segments; it is invalid by design. Depth cap is a feature.
- **Suggestion always returned on mismatch**: rejection-only is not enough for ADHD users who forgot the exact schema.
- **`schema_version` is a zero-padded string `"001"`**, not an integer. Reason: keeps consistent with the tag suffix convention and avoids JS integer overflow concerns if the JSON is ever parsed in a browser context.
- **`schema_version` is first key**: any consumer can fast-path the version check without scanning the full object.

## Out of Scope

- Retroactive validation of existing vault files.
- Auto-generating tags from note content.
- `vault_io.py` read/write primitives (separate planned item, not blocking this).
- Bumping `schema_version` beyond `"001"` (happens only with a future breaking shape change).
