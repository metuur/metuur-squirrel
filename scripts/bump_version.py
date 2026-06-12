#!/usr/bin/env python3
"""bump_version.py — sync every Squirrel manifest to a single bumped version.

The DMG version label reads only apps/cli/pyproject.toml, but the repo's other
manifests have drifted (0.1.0 / 0.5.0 / 0.7.0). This script treats
apps/cli/pyproject.toml as the canonical source, bumps it, and writes the SAME
new version into all manifests so they stay in sync.

Usage:
    python3 scripts/bump_version.py <patch|minor|major>

Edits files in place. Does NOT git add, commit, or tag — review the diff first.
Lockfiles (package-lock.json) are intentionally skipped; npm regenerates them.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "apps/cli/pyproject.toml"

# (path, regex). The regex must have two capture groups bracketing the version
# value: group 1 = everything up to and including the opening quote, group 2 =
# the closing quote. count=1 means only the FIRST match is replaced — for every
# target below the first match is the package/app version (dependency versions
# appear later in the file and are left untouched).
TOML_VERSION = r'^(version\s*=\s*")[^"]+(")'
JSON_VERSION = r'("version"\s*:\s*")[^"]+(")'

TARGETS = [
    ("apps/cli/pyproject.toml", TOML_VERSION),
    ("apps/backend/pyproject.toml", TOML_VERSION),
    ("apps/desktop/src-tauri/Cargo.toml", TOML_VERSION),   # first match = [package]
    ("apps/desktop/src-tauri/tauri.conf.json", JSON_VERSION),
    ("package.json", JSON_VERSION),
    ("apps/desktop/package.json", JSON_VERSION),
    ("apps/backend/app/package.json", JSON_VERSION),
    ("apps/cli/squirrel", JSON_VERSION),                   # hardcoded plugin version
    ("agent-pack/.claude-plugin/plugin.json", JSON_VERSION),  # web-UI version via _detect_version()
]


def read_canonical() -> str:
    m = re.search(r'^version\s*=\s*"([^"]+)"', CANONICAL.read_text(encoding="utf-8"), re.M)
    if not m:
        sys.exit(f"error: could not find a version in {CANONICAL}")
    return m.group(1)


def bump(version: str, part: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        sys.exit(f"error: version {version!r} is not semver X.Y.Z — cannot bump")
    major, minor, patch = (int(p) for p in parts)
    if part == "patch":
        patch += 1
    elif part == "minor":
        minor, patch = minor + 1, 0
    elif part == "major":
        major, minor, patch = major + 1, 0, 0
    else:
        sys.exit(f"error: part must be patch|minor|major, got {part!r}")
    return f"{major}.{minor}.{patch}"


def apply(path_rel: str, pattern: str, new_version: str) -> None:
    path = ROOT / path_rel
    if not path.is_file():
        print(f"  skip (absent): {path_rel}")
        return
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(pattern, r"\g<1>" + new_version + r"\g<2>",
                          text, count=1, flags=re.M)
    if n == 0:
        print(f"  ⚠ no version match in {path_rel} — left unchanged")
        return
    if new_text == text:
        print(f"  = {path_rel} (already {new_version})")
        return
    path.write_text(new_text, encoding="utf-8")
    print(f"  ✓ {path_rel}")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: bump_version.py <patch|minor|major>")
    part = sys.argv[1].strip().lower()
    current = read_canonical()
    new_version = bump(current, part)
    print(f"🔖  bump {part}: {current} → {new_version}")
    for path_rel, pattern in TARGETS:
        apply(path_rel, pattern, new_version)
    print(f"\nDone. All manifests set to {new_version}. Files edited, not committed.")


if __name__ == "__main__":
    main()
