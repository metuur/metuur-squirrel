#!/usr/bin/env python3
"""
lib/config_loader.py — Multi-vault config loader for Squirrel.

The single entry point for any Squirrel tool (slash command, CLI, skill, future
web UI) to read or write `~/.squirrel/config.toml`. Centralises the multi-vault
schema, validation, and state-file resolution.

Public API:

    list_vaults(config_path=None)             -> list[Vault]
    get_vault(name=None, config_path=None)    -> Vault
    get_default_vault(config_path=None)       -> Vault
    add_vault(name, path, config_path=None)   -> Vault
    remove_vault(name, config_path=None)      -> None
    set_default(name, config_path=None)       -> None
    state_file_for(name, state_dir=None)      -> pathlib.Path
    read_state(name, state_dir=None)          -> dict
    write_state(name, data, state_dir=None)   -> None

Exceptions:

    ConfigError              — malformed file or schema invariant violation
    ValidationError          — input rejected (subclass of ConfigError)
    VaultNotFoundError       — get_vault(name=...) where name not configured
    NoVaultsConfiguredError  — config absent or [[vaults]] array empty

Write API contract:

    All write operations (add_vault, remove_vault, set_default) edit the
    config file in place via line-based surgical edits — comments, other
    sections, and formatting are preserved. Atomic via temp file + os.replace.

Python 3.9+ compatible. Uses `tomllib` on 3.11+ with a minimal fallback parser
for 3.9 / 3.10 that covers the Squirrel schema subset only.

Spec source: docs/ears/multi-vault-core.md  (units 1, 3, 8)
"""

from __future__ import annotations

import pathlib
import sys
from typing import NamedTuple, Optional


# ─── Public types ────────────────────────────────────────────────────────────


class Vault(NamedTuple):
    """A configured Squirrel vault."""
    name: str
    path: pathlib.Path
    default: bool


class ConfigError(Exception):
    """Raised when the config file is malformed or violates invariants."""


class VaultNotFoundError(ConfigError):
    """Raised when get_vault(name) is called with a non-existent name."""


class NoVaultsConfiguredError(ConfigError):
    """Raised when no vaults are configured at all."""


class ValidationError(ConfigError):
    """Raised when input to a write operation is rejected (bad path,
    duplicate name, removing the default, etc.)."""


# ─── Module-level defaults ───────────────────────────────────────────────────


DEFAULT_CONFIG_PATH = pathlib.Path("~/.squirrel/config.toml").expanduser()
DEFAULT_STATE_DIR = pathlib.Path("~/.squirrel/state").expanduser()


# ─── TOML loading ────────────────────────────────────────────────────────────


def _load_toml(path: pathlib.Path) -> dict:
    """Load TOML from `path`. Uses tomllib (3.11+) when available, else fallback."""
    if sys.version_info >= (3, 11):
        import tomllib  # type: ignore[import-not-found]
        with open(path, "rb") as f:
            return tomllib.load(f)
    return _fallback_parse(path.read_text(encoding="utf-8"))


def _fallback_parse(text: str) -> dict:
    """Minimal TOML parser covering Squirrel's config schema.

    Supports:
      - top-level scalar `key = value`
      - `[section]` tables with scalar keys
      - `[[array_of_tables]]` with scalar keys
      - inline `key = [..., ...]` arrays of strings
      - `#` line comments and trailing comments
      - string values (double or single quoted), bool (true/false), int, float
      - leading-tilde paths kept verbatim (expanded later by Vault.path)

    Does NOT support: inline tables, nested arrays, multi-line strings, dates,
    or `+` integer prefix. The Squirrel config schema does not use any of
    these.
    """
    result: dict = {}
    current_section: dict = result

    for raw_line in text.splitlines():
        line = _strip_comment(raw_line).rstrip()
        s = line.strip()
        if not s:
            continue

        # Array of tables: [[name]]
        if s.startswith("[[") and s.endswith("]]"):
            name = s[2:-2].strip()
            arr = result.setdefault(name, [])
            new_table: dict = {}
            arr.append(new_table)
            current_section = new_table
            continue

        # Section table: [name]
        if s.startswith("[") and s.endswith("]"):
            name = s[1:-1].strip()
            current_section = result.setdefault(name, {})
            continue

        # key = value
        if "=" in s:
            key, _, raw_val = s.partition("=")
            current_section[key.strip()] = _parse_value(raw_val.strip())

    return result


def _strip_comment(s: str) -> str:
    """Strip a trailing `#` comment, respecting quoted strings."""
    in_string = False
    quote_char = ""
    for i, ch in enumerate(s):
        if in_string:
            if ch == quote_char:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote_char = ch
            elif ch == "#":
                return s[:i]
    return s


def _parse_value(s: str):
    """Parse a TOML scalar or simple inline array."""
    if s == "true":
        return True
    if s == "false":
        return False

    # Quoted string
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        return s[1:-1]

    # Inline array of strings (or bare tokens)
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        items = []
        for item in _split_array(inner):
            item = item.strip()
            if not item:
                continue
            if len(item) >= 2 and (
                (item[0] == '"' and item[-1] == '"') or (item[0] == "'" and item[-1] == "'")
            ):
                items.append(item[1:-1])
            else:
                items.append(_parse_value(item))
        return items

    # Numbers
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        pass

    # Bare token — keep as-is (shouldn't appear in our schema, but be lenient)
    return s


def _split_array(inner: str) -> list[str]:
    """Split a comma-separated array body, respecting quoted strings."""
    out: list[str] = []
    buf: list[str] = []
    in_string = False
    quote_char = ""
    for ch in inner:
        if in_string:
            buf.append(ch)
            if ch == quote_char:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote_char = ch
                buf.append(ch)
            elif ch == ",":
                out.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


# ─── Internal: build Vault list from raw config dict ─────────────────────────


def _vaults_from_config(cfg: dict) -> list[Vault]:
    """Parse, validate, and return the [[vaults]] list as Vault namedtuples."""
    raw = cfg.get("vaults", [])
    if not isinstance(raw, list):
        raise ConfigError(f"'vaults' must be an array of tables, got {type(raw).__name__}")
    if not raw:
        if "vault_path" in cfg:
            # Legacy single-vault config. Migration is implemented in story 1.4
            # of multi-vault-core; until that lands, surface a clear error so
            # callers don't silently produce wrong results.
            raise ConfigError(
                "Legacy config detected (vault_path present, no [[vaults]] array). "
                "Run /sq-init or wait for the migration to be applied."
            )
        raise NoVaultsConfiguredError(
            "No vaults configured. Run /sq-init or `squirrel vaults add`."
        )

    out: list[Vault] = []
    seen: set[str] = set()
    default_count = 0
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ConfigError(f"vaults[{i}] must be a table")
        name = entry.get("name")
        path_s = entry.get("path")
        default = entry.get("default", False)
        if not isinstance(name, str) or not name:
            raise ConfigError(f"vaults[{i}] missing or invalid 'name'")
        if not isinstance(path_s, str) or not path_s:
            raise ConfigError(f"vaults[{i}] missing or invalid 'path'")
        if not isinstance(default, bool):
            raise ConfigError(f"vaults[{i}].default must be a boolean")
        if name in seen:
            raise ConfigError(f"duplicate vault name: {name!r}")
        seen.add(name)
        if default:
            default_count += 1
        out.append(Vault(name=name, path=pathlib.Path(path_s).expanduser(), default=default))

    if default_count == 0:
        raise ConfigError("no vault marked default = true; exactly one is required")
    if default_count > 1:
        raise ConfigError(f"expected exactly one default = true, got {default_count}")
    return out


# ─── Public API: read ────────────────────────────────────────────────────────


def list_vaults(config_path: Optional[pathlib.Path] = None) -> list[Vault]:
    """Return the configured vaults in config-file order.

    Triggers lazy migration of legacy single-vault configs (R-2.1).

    Raises:
        NoVaultsConfiguredError: file missing or [[vaults]] empty.
        ConfigError: schema invariants violated.
    """
    path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise NoVaultsConfiguredError(
            f"No config at {path}. Run /sq-init or `squirrel vaults add`."
        )
    # Lazy in-process migration of legacy single-vault schemas
    migrate_legacy(config_path=path)
    return _vaults_from_config(_load_toml(path))


def get_vault(
    name: Optional[str] = None,
    config_path: Optional[pathlib.Path] = None,
) -> Vault:
    """Return a single Vault.

    With name=None: returns the default vault.
    With name="X": returns the vault named X, or raises VaultNotFoundError.
    """
    vaults = list_vaults(config_path=config_path)
    if name is None:
        for v in vaults:
            if v.default:
                return v
        # Defensive: _vaults_from_config validates this, but guard anyway.
        raise ConfigError("no default vault configured")
    for v in vaults:
        if v.name == name:
            return v
    valid = [v.name for v in vaults]
    raise VaultNotFoundError(
        f"vault {name!r} not found. Available: {', '.join(valid)}"
    )


def get_default_vault(config_path: Optional[pathlib.Path] = None) -> Vault:
    """Return the default vault."""
    return get_vault(name=None, config_path=config_path)


def state_file_for(
    name: str,
    state_dir: Optional[pathlib.Path] = None,
) -> pathlib.Path:
    """Return the per-vault state file path. Creates the parent directory if missing.

    Example:
        state_file_for("personal") -> ~/.squirrel/state/personal.json
    """
    base = state_dir if state_dir is not None else DEFAULT_STATE_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{name}.json"


def read_state(
    name: str,
    state_dir: Optional[pathlib.Path] = None,
) -> dict:
    """Read per-vault state. Returns {} if the file does not exist.

    State schema (preserved across reads/writes): `current_project`,
    `current_intent`, `last_switch_at`, `switch_ledger`. Callers may store
    additional keys; they are preserved as-is.
    """
    import json
    p = state_file_for(name, state_dir=state_dir)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def write_state(
    name: str,
    data: dict,
    state_dir: Optional[pathlib.Path] = None,
) -> None:
    """Write per-vault state atomically (temp file + os.replace).

    Caller is responsible for preserving any keys it does not own. Read,
    modify, write is the standard pattern.
    """
    import json
    p = state_file_for(name, state_dir=state_dir)
    _atomic_write(p, json.dumps(data, indent=2, default=str) + "\n")


# ─── Public API: migration ───────────────────────────────────────────────────


def migrate_legacy(
    config_path: Optional[pathlib.Path] = None,
    *,
    state_dir: Optional[pathlib.Path] = None,
) -> bool:
    """Migrate a legacy single-vault config in place to the multi-vault schema.

    Lazy and idempotent: returns True if migration ran, False otherwise.
    Triggered automatically by `list_vaults`; can also be called explicitly.

    The legacy schema has top-level `vault_path` and optional `environment_name`.
    The migration:
      - converts `vault_path` + `environment_name` into a single [[vaults]]
        entry with default = true
      - renames `environment_name` → `machine_environment`
      - prepends `# Auto-migrated <ISO-date>` as line 1
      - moves `~/.squirrel/state.json` to `~/.squirrel/state/<name>.json` if it
        exists
      - preserves every other line and comment
    """
    import datetime
    import os

    cfg_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        return False

    text = cfg_path.read_text(encoding="utf-8")

    # Quick check: already migrated?
    if "[[vaults]]" in text:
        return False

    # Quick check: anything to migrate?
    has_legacy_path = False
    for raw_line in text.splitlines():
        stripped = _strip_comment(raw_line).strip()
        if stripped.startswith("vault_path") and "=" in stripped:
            has_legacy_path = True
            break
    if not has_legacy_path:
        # Nothing to migrate (and no [[vaults]] either — caller will raise)
        return False

    # Parse just enough to capture the values being migrated
    legacy_vault_path: Optional[str] = None
    legacy_env_name: Optional[str] = None
    lines = text.splitlines(keepends=False)
    keep_lines: list[str] = []

    # Track whether we've seen any [section] yet — that's where we insert
    # the new [[vaults]] block (before the first section)
    insertion_marker_idx: Optional[int] = None

    for i, raw_line in enumerate(lines):
        stripped = _strip_comment(raw_line).strip()

        if stripped.startswith("vault_path") and "=" in stripped:
            _, _, raw_val = stripped.partition("=")
            parsed = _parse_value(raw_val.strip())
            if isinstance(parsed, str):
                legacy_vault_path = parsed
            # Drop this line
            continue

        if stripped.startswith("environment_name") and "=" in stripped:
            _, _, raw_val = stripped.partition("=")
            parsed = _parse_value(raw_val.strip())
            if isinstance(parsed, str):
                legacy_env_name = parsed
            # Rewrite this line to use machine_environment
            indent = raw_line[: len(raw_line) - len(raw_line.lstrip())]
            keep_lines.append(f'{indent}machine_environment = "{parsed}"')
            continue

        # Track first section header — insertion happens just before it
        if (
            insertion_marker_idx is None
            and stripped.startswith("[")
            and stripped.endswith("]")
            and not stripped.startswith("[[")
        ):
            insertion_marker_idx = len(keep_lines)

        keep_lines.append(raw_line)

    if legacy_vault_path is None:
        # vault_path matched the quick check but disappeared during parse —
        # defensive: don't migrate.
        return False

    # Build the new [[vaults]] entry
    vault_name = legacy_env_name if legacy_env_name else "default"
    vault_entry = _format_vault_entry(
        vault_name, legacy_vault_path, default=True
    )

    # Determine insertion point
    if insertion_marker_idx is None:
        # No sections after the migrated scalars — append at end
        out_lines = keep_lines[:]
        if out_lines and out_lines[-1].strip() != "":
            out_lines.append("")
        out_lines.append(vault_entry.rstrip("\n"))
    else:
        # Insert before the first section, with blank separators
        before = keep_lines[:insertion_marker_idx]
        after = keep_lines[insertion_marker_idx:]
        # Trim trailing blank lines from `before` so we control spacing
        while before and before[-1].strip() == "":
            before.pop()
        out_lines = before + [""] + [vault_entry.rstrip("\n")] + [""] + after

    # Prepend the auto-migrated comment
    iso_date = datetime.date.today().isoformat()
    new_text = f"# Auto-migrated {iso_date}\n" + "\n".join(out_lines)
    if not new_text.endswith("\n"):
        new_text += "\n"

    _atomic_write(cfg_path, new_text)

    # Move ~/.squirrel/state.json -> ~/.squirrel/state/<name>.json
    base_state_dir = state_dir if state_dir is not None else DEFAULT_STATE_DIR
    legacy_state = base_state_dir.parent / "state.json"
    if legacy_state.is_file():
        base_state_dir.mkdir(parents=True, exist_ok=True)
        target = base_state_dir / f"{vault_name}.json"
        if not target.exists():
            os.replace(legacy_state, target)

    return True


# ─── Internal: line-based surgical edits ─────────────────────────────────────


def _atomic_write(path: pathlib.Path, text: str) -> None:
    """Write `text` to `path` atomically (temp file + os.replace)."""
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _vault_block_ranges(lines: list[str]) -> list[tuple[str, int, int]]:
    """Locate each `[[vaults]]` block in the source lines.

    Returns a list of (name, start_line, end_line) tuples, where `start_line`
    is the index of the `[[vaults]]` header and `end_line` is the index of
    the last line that belongs to that block (inclusive). The block ends
    at the next `[section]` or `[[section]]` line, or end of file.
    """
    out: list[tuple[str, int, int]] = []
    i = 0
    n = len(lines)
    while i < n:
        stripped = _strip_comment(lines[i]).strip()
        if stripped == "[[vaults]]":
            block_start = i
            i += 1
            # Scan forward to find the end of this block
            block_end = block_start
            name = ""
            while i < n:
                s = _strip_comment(lines[i]).strip()
                if s.startswith("[") and s != "":
                    # Next section starts
                    break
                if s.startswith("name") and "=" in s:
                    _, _, raw_val = s.partition("=")
                    parsed = _parse_value(raw_val.strip())
                    if isinstance(parsed, str):
                        name = parsed
                if s:
                    block_end = i
                i += 1
            out.append((name, block_start, block_end))
        else:
            i += 1
    return out


def _format_vault_entry(name: str, path: str, default: bool) -> str:
    """Format a [[vaults]] block as text. Always ends with a trailing newline."""
    default_str = "true" if default else "false"
    return (
        f"[[vaults]]\n"
        f'name = "{name}"\n'
        f'path = "{path}"\n'
        f"default = {default_str}\n"
    )


# ─── Public API: write ───────────────────────────────────────────────────────


def add_vault(
    name: str,
    path: str,
    *,
    config_path: Optional[pathlib.Path] = None,
) -> Vault:
    """Append a new vault entry to the config.

    The new vault is added with `default = false` UNLESS no config or no vaults
    exist yet, in which case it is created with `default = true` (bootstrap).

    Raises:
        ValidationError: name already exists, path does not exist, or path is
            not a directory.
    """
    cfg_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH

    # Validate path (must exist and be a directory)
    path_obj = pathlib.Path(path).expanduser()
    if not path_obj.exists():
        raise ValidationError(f"path does not exist: {path}")
    if not path_obj.is_dir():
        raise ValidationError(f"path is not a directory: {path}")
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("vault name must be a non-empty string")

    # Bootstrap path: no config file or empty file
    if not cfg_path.exists() or not cfg_path.read_text(encoding="utf-8").strip():
        entry = _format_vault_entry(name, path, default=True)
        _atomic_write(cfg_path, entry + "\n")
        return Vault(name=name, path=path_obj, default=True)

    # Existing config — validate against current vaults
    try:
        existing = list_vaults(config_path=cfg_path)
    except NoVaultsConfiguredError:
        # Config exists but has no [[vaults]] (e.g., legacy or partial)
        existing = []
    if any(v.name == name for v in existing):
        raise ValidationError(f"vault name already exists: {name!r}")

    # Append the new block to the file. If [[vaults]] exists already, insert
    # right after the last block; otherwise append at end of file.
    text = cfg_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=False)
    ranges = _vault_block_ranges(lines)
    new_entry = _format_vault_entry(name, path, default=False)

    if ranges:
        # Insert after the last [[vaults]] block, preserving any blank
        # separators that already exist after it.
        _, _, last_end = ranges[-1]
        insert_at = last_end + 1
        prefix = lines[:insert_at]
        suffix = lines[insert_at:]
        # Ensure there's a blank line between the existing block and the new one
        prefix_text = "\n".join(prefix)
        if prefix_text and not prefix_text.endswith("\n"):
            prefix_text += "\n"
        if not prefix_text.endswith("\n\n"):
            prefix_text += "\n"
        suffix_text = "\n".join(suffix)
        new_text = prefix_text + new_entry
        if suffix_text:
            new_text = new_text.rstrip("\n") + "\n\n" + suffix_text
            if not new_text.endswith("\n"):
                new_text += "\n"
    else:
        # No existing [[vaults]] — append at end
        if text and not text.endswith("\n"):
            text += "\n"
        if text and not text.endswith("\n\n"):
            text += "\n"
        new_text = text + new_entry

    _atomic_write(cfg_path, new_text)
    return Vault(name=name, path=path_obj, default=False)


def remove_vault(
    name: str,
    *,
    config_path: Optional[pathlib.Path] = None,
) -> None:
    """Remove the named vault from the config.

    Raises:
        ValidationError: if the named vault is the default — caller must set
            another vault as default first.
        VaultNotFoundError: if no vault with that name exists.
    """
    cfg_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    vaults = list_vaults(config_path=cfg_path)  # raises if config missing

    target = None
    for v in vaults:
        if v.name == name:
            target = v
            break
    if target is None:
        valid = [v.name for v in vaults]
        raise VaultNotFoundError(
            f"vault {name!r} not found. Available: {', '.join(valid)}"
        )
    if target.default:
        others = [v.name for v in vaults if v.name != name]
        raise ValidationError(
            f"refusing to remove the default vault {name!r}. "
            f"Set another vault as default first via `squirrel vaults default <name>`. "
            f"Other vaults: {', '.join(others) or '(none)'}"
        )

    text = cfg_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=False)
    ranges = _vault_block_ranges(lines)

    target_range = None
    for entry_name, start, end in ranges:
        if entry_name == name:
            target_range = (start, end)
            break
    if target_range is None:
        raise ConfigError(
            f"vault {name!r} validated but block not found in source — file likely malformed"
        )

    start, end = target_range
    # Consume any single trailing blank separator line after the block
    drop_end = end
    if drop_end + 1 < len(lines) and lines[drop_end + 1].strip() == "":
        drop_end += 1

    new_lines = lines[:start] + lines[drop_end + 1 :]
    new_text = "\n".join(new_lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    _atomic_write(cfg_path, new_text)


def set_default(
    name: str,
    *,
    config_path: Optional[pathlib.Path] = None,
) -> None:
    """Set `name` as the default vault. Clears the flag on every other vault.

    Raises:
        VaultNotFoundError: if no vault with that name exists.
    """
    cfg_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    vaults = list_vaults(config_path=cfg_path)
    if not any(v.name == name for v in vaults):
        valid = [v.name for v in vaults]
        raise VaultNotFoundError(
            f"vault {name!r} not found. Available: {', '.join(valid)}"
        )

    text = cfg_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=False)
    ranges = _vault_block_ranges(lines)

    # For each block, locate its `default = ...` line and rewrite the value.
    for entry_name, start, end in ranges:
        new_value = "true" if entry_name == name else "false"
        for i in range(start, end + 1):
            stripped = _strip_comment(lines[i]).strip()
            if stripped.startswith("default") and "=" in stripped:
                # Preserve original indentation
                indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
                lines[i] = f"{indent}default = {new_value}"
                break

    new_text = "\n".join(lines)
    if not new_text.endswith("\n"):
        new_text += "\n"
    _atomic_write(cfg_path, new_text)
