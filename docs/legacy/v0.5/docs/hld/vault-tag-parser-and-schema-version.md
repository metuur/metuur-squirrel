# Vault Tag Parser & Contract Versioning — High-Level Design

## Overview

Two connected gaps in the `vault` segment: the tag schema (`PROYECTO-SUBÁREA-COMPONENTE-NNN`) has no enforcement code — any string can be written as a tag today — and the JSON contract emitted by `status_aggregator.py --json` has no `schema_version` field, making it impossible to detect breaking shape changes downstream. This ships `lib/tag_parser.py` (VAULT-003) and adds `schema_version` to the aggregator contract (VAULT-005).

## Stakeholders & Impact

**Primary user — developer creating intents via `/sq-capture`, `/sq-init`, or directly in Obsidian.**
Today: a typo like `visa-001` or `VISA-001` (only 2 segments) silently writes a malformed tag. Dataview queries that group by `proyecto` field break silently. The user never knows.
After: invalid tags are caught at write time with a concrete suggestion (`visa-001` → `VISA-MISC-TASK-001`).

**Secondary consumer — `status_aggregator.py` and Dataview templates.**
Today: tags are stored and re-emitted as-is; grouping is unreliable.
After: tag_parser is the single normalisation point; any consumer can call it before grouping.

**Future consumers — any agent or script reading the `--json` output.**
Today: the JSON shape can change without any signal.
After: `schema_version` lets consumers detect and handle breaking changes.

## Goals

- `lib/tag_parser.py` is the sole authority for tag validation and normalisation.
- Invalid tags return a suggested corrected form, not just a rejection.
- Tags with fewer than 3 named segments are structurally invalid (depth cap is a feature, not a limitation).
- Tag is optional in capture flows — parser gracefully handles `None` / empty input.
- `status_aggregator.py --json` always emits `schema_version: "001"` as its first key.

## Non-Goals

- Auto-generating tags from note content (suggestion yes, full auto-gen no).
- Enforcing tags retroactively on existing vault files.
- Changing the tag schema itself (schema is already defined in VAULT-003 EARS).

## Success Criteria

- `python3 lib/tag_parser.py VISA-001` prints invalid + suggestion.
- `python3 lib/tag_parser.py VISA-FAMILIA-TRAMITE-001` prints valid.
- `python3 lib/status_aggregator.py --json` output contains `"schema_version": "001"` as first key.
- 68 existing tests still pass; new tests cover tag_parser and schema_version.
