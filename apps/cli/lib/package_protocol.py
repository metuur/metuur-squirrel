#!/usr/bin/env python3
"""
Context Bridge Package Protocol — generación y validación de paquetes.

Usado por las skills sync-out y sync-in.
stdlib only — no dependencias externas.

Uso CLI:
    python package_protocol.py generate --vault ~/vault --scope TAG --to work
    python package_protocol.py parse --input package.md
    python package_protocol.py validate --input package.md
    python package_protocol.py apply --input package.md --vault ~/vault [--dry-run]
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


PACKAGE_VERSION = "v1"
START_MARKER = f"<!-- SQUIRREL-PACKAGE {PACKAGE_VERSION} -->"
END_MARKER = "<!-- END-SQUIRREL-PACKAGE -->"

# @spec SYNC-007


# ─────────────────────────────────────────────────────────────────────────────
# Compliance scan — detect sensitive content before packaging
# ─────────────────────────────────────────────────────────────────────────────

SENSITIVE_PATTERNS = [
    # API keys / tokens
    (re.compile(r"sk-[a-zA-Z0-9]{32,}"), "OpenAI API key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "GitHub PAT"),
    (re.compile(r"xox[baprs]-[a-zA-Z0-9-]{10,}"), "Slack token"),
    # Generic
    (re.compile(r'(api[_-]?key|secret|password|token)\s*[:=]\s*["\']([^"\']{8,})["\']', re.IGNORECASE), "credential-like"),
    # PII
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN-like"),
    (re.compile(r"\b(?:\d[ -]*?){13,19}\b"), "credit-card-like"),
]


def scan_for_sensitive(content: str) -> list[tuple[int, str, str]]:
    """Return list of (line_number, pattern_name, snippet) for any sensitive matches."""
    findings = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        for pattern, name in SENSITIVE_PATTERNS:
            if pattern.search(line):
                snippet = line.strip()[:80]
                findings.append((line_num, name, snippet))
    return findings


# ─────────────────────────────────────────────────────────────────────────────
# Hash computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_payload_hash(files: list[dict]) -> str:
    """
    Compute SHA-256 of the canonical payload.
    Files must be a list of {"target_path": str, "content": str}, ordered.
    """
    parts = []
    for f in files:
        parts.append(f["target_path"])
        parts.append(f["content"])
    canonical = "\n---PACKAGE-SEPARATOR---\n".join(parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Generation
# ─────────────────────────────────────────────────────────────────────────────

# @spec SYNC-002
def collect_files_by_scope(vault_path: Path, scope: str) -> list[dict]:
    """
    Resolve a scope string into a list of file dicts.

    Scopes:
        TAG                       — single file matching <TAG>.md
        PROJECT:*                 — all files in 01-Active-Projects/<PROJECT>/
        PROJECT:research          — files with `tipo: research` in project folder
        PROJECT:decisions         — files with `tipo: decision` in project folder
    """
    files = []

    if ":" in scope:
        project, kind = scope.split(":", 1)
    else:
        # Treat as a single TAG
        # Find the file by name
        for p in vault_path.rglob(f"{scope}.md"):
            if vault_path in p.parents or p.parent == vault_path:
                files.append({
                    "target_path": str(p.relative_to(vault_path)),
                    "operation": "create",
                    "tag": scope,
                    "conflict_policy": "ask",
                    "content": p.read_text(encoding="utf-8"),
                    "description": _extract_title(p.read_text(encoding="utf-8")),
                })
        return files

    project_dir = vault_path / "01-Active-Projects" / project
    if not project_dir.exists():
        # Try in areas
        project_dir = vault_path / "03-Areas"
        if not project_dir.exists():
            return []

    for md_file in project_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(content)

        # Filter by kind
        if kind == "*":
            pass  # include all
        elif kind == "research" and frontmatter.get("type") != "research":
            continue
        elif kind == "decisions" and frontmatter.get("type") != "decision":
            continue
        elif kind not in ("*", "research", "decisions"):
            # Unknown kind, skip
            continue

        files.append({
            "target_path": str(md_file.relative_to(vault_path)),
            "operation": "create",  # default — caller can override
            "tag": frontmatter.get("id", md_file.stem),
            "conflict_policy": "ask",
            "content": content,
            "description": _extract_title(content),
        })

    return files


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter (very simple parser, no dependencies)."""
    fm = {}
    if not content.startswith("---"):
        return fm
    lines = content.splitlines()
    if len(lines) < 2:
        return fm
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return fm
    for line in lines[1:end_idx]:
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def _extract_title(content: str) -> str:
    """Extract H1 title from markdown content."""
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "(no title)"


# @spec SYNC-001
def generate_package(
    files: list[dict],
    from_env: str,
    to_env: str,
    scope: str,
    intent: str = "",
    agent_name: str = "context-bridge",
    hostname: str = "",
) -> str:
    """Generate the full package Markdown string."""
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    human_date = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
    payload_hash = compute_payload_hash(files)

    header = f"""{START_MARKER}
<!--
  from: {from_env}
  to: {to_env}
  generated_at: {ts}
  generated_by: {agent_name}@{hostname or os.uname().nodename}
  scope: {scope}
  files_count: {len(files)}
  hash_sha256: {payload_hash}
  intent: {intent or 'manual-export'}
  receiver_instructions: apply-with-sync-in
-->

# 📦 Context Bridge Package

**De**: {from_env}  →  **Para**: {to_env}
**Generado**: {human_date}
**Scope**: {scope}
**Archivos**: {len(files)}

> 📋 Para aplicar: en el otro entorno, abrí Claude Code / Codex y pegá ESTE bloque completo
> en el chat. El skill `context-bridge:sync-in` lo procesará automáticamente.

---

## 📑 Resumen del paquete

"""

    summary_lines = []
    for f in files:
        summary_lines.append(f"- `{f['target_path']}` — {f['operation']} — {f.get('description', '')}")

    files_section = "\n\n---\n\n## 📂 Archivos a aplicar\n"

    for i, f in enumerate(files, start=1):
        files_section += f"""
### Archivo {i}: {f['target_path']}

**Operación**: {f['operation']}
**Tag**: `{f['tag']}`
**Conflicto si existe**: {f['conflict_policy']}

```markdown
{f['content']}
```

---
"""

    footer = f"\n{END_MARKER}\n"

    return header + "\n".join(summary_lines) + files_section + footer


# ─────────────────────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_package(content: str) -> dict:
    """
    Parse a package string into structured dict.

    Returns:
        {
            "header": {...},
            "files": [{"target_path", "operation", "tag", "conflict_policy", "content"}, ...]
        }

    Raises:
        ValueError if package is malformed.
    """
    start = content.find(START_MARKER)
    end = content.find(END_MARKER)
    if start == -1:
        raise ValueError(f"Missing start marker: {START_MARKER}")
    if end == -1:
        raise ValueError(f"Missing end marker: {END_MARKER}")
    if end < start:
        raise ValueError("End marker before start marker")

    body = content[start:end + len(END_MARKER)]

    # Parse header (HTML comment after start marker)
    header_match = re.search(r"<!--\s*\n(.*?)\n-->", body, re.DOTALL)
    if not header_match:
        raise ValueError("Missing or malformed header comment")
    header_text = header_match.group(1)
    header = {}
    for line in header_text.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            header[key.strip()] = val.strip()

    # Parse files — each starts with "### Archivo N:"
    file_pattern = re.compile(
        r"###\s+Archivo\s+(\d+):\s+(.+?)\n\n"
        r"\*\*Operación\*\*:\s+(.+?)\n"
        r"\*\*Tag\*\*:\s+`(.+?)`\n"
        r"\*\*Conflicto si existe\*\*:\s+(.+?)\n\n"
        r"```markdown\n(.*?)\n```",
        re.DOTALL,
    )

    files = []
    for match in file_pattern.finditer(body):
        files.append({
            "index": int(match.group(1)),
            "target_path": match.group(2).strip(),
            "operation": match.group(3).strip(),
            "tag": match.group(4).strip(),
            "conflict_policy": match.group(5).strip(),
            "content": match.group(6),
        })

    return {"header": header, "files": files}


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

# @spec SYNC-003
def validate_package(package: dict) -> tuple[bool, list[str]]:
    """Validate a parsed package. Returns (is_valid, list_of_errors)."""
    errors = []

    header = package["header"]
    required = ["from", "to", "generated_at", "scope", "files_count", "hash_sha256"]
    for key in required:
        if key not in header:
            errors.append(f"Missing header field: {key}")

    if errors:
        return False, errors

    declared_count = int(header.get("files_count", 0))
    actual_count = len(package["files"])
    if declared_count != actual_count:
        errors.append(
            f"files_count mismatch: header says {declared_count}, found {actual_count}"
        )

    expected_hash = header["hash_sha256"]
    actual_hash = compute_payload_hash([
        {"target_path": f["target_path"], "content": f["content"]}
        for f in package["files"]
    ])
    if expected_hash != actual_hash:
        errors.append(
            f"Hash mismatch:\n  expected: {expected_hash}\n  computed: {actual_hash}\n"
            f"  → package may be truncated or modified."
        )

    # Path safety
    for f in package["files"]:
        if ".." in f["target_path"] or f["target_path"].startswith("/"):
            errors.append(f"Unsafe path in file: {f['target_path']}")

    return len(errors) == 0, errors


# ─────────────────────────────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────────────────────────────

# @spec SYNC-005, SYNC-006, SYNC-008
def apply_package(
    package: dict,
    vault_path: Path,
    dry_run: bool = False,
    interactive: bool = True,
) -> dict:
    """
    Apply a parsed package to the vault.

    Returns a result dict with counts of created/updated/skipped/failed.
    """
    result = {"created": 0, "updated": 0, "skipped": 0, "failed": 0, "details": []}

    vault_path = vault_path.resolve()

    # SYNC-006: idempotency — if this package hash is already in audit log, no-op
    if not dry_run:
        pkg_hash = package["header"].get("hash_sha256", "")
        applied_dir = vault_path / ".squirrel" / "applied"
        if pkg_hash and applied_dir.exists():
            for audit_file in applied_dir.glob("*.json"):
                try:
                    audit = json.loads(audit_file.read_text(encoding="utf-8"))
                    if audit.get("package_hash") == pkg_hash:
                        result["already_applied"] = True
                        result["audit_log"] = str(audit_file)
                        return result
                except (json.JSONDecodeError, OSError):
                    continue

    for f in package["files"]:
        target = (vault_path / f["target_path"]).resolve()

        # Path safety check (defense in depth)
        try:
            target.relative_to(vault_path)
        except ValueError:
            result["failed"] += 1
            result["details"].append({
                "path": str(f["target_path"]),
                "result": "failed",
                "reason": "path-traversal-attempt",
            })
            continue

        exists = target.exists()
        op = f["operation"]

        if op == "create" and exists:
            if f["conflict_policy"] == "skip":
                result["skipped"] += 1
                result["details"].append({"path": str(f["target_path"]), "result": "skipped-exists"})
                continue
            elif f["conflict_policy"] == "ask" and interactive:
                # Print a prompt; in non-interactive mode, default to skip
                print(f"\n⚠️ Conflict: {f['target_path']} already exists.")
                print(f"   [o]verwrite / [s]kip / [c]onflict-suffix")
                choice = input("   → ").strip().lower() or "s"
                if choice == "s":
                    result["skipped"] += 1
                    result["details"].append({"path": str(f["target_path"]), "result": "skipped-conflict"})
                    continue
                elif choice == "c":
                    target = target.with_name(target.stem + "-CONFLICT" + target.suffix)
                # else: overwrite

        if dry_run:
            result["details"].append({
                "path": str(f["target_path"]),
                "result": "dry-run",
                "operation": op,
            })
            continue

        target.parent.mkdir(parents=True, exist_ok=True)

        if op == "append" and exists:
            existing = target.read_text(encoding="utf-8")
            target.write_text(existing + "\n\n" + f["content"], encoding="utf-8")
            result["updated"] += 1
            result["details"].append({"path": str(f["target_path"]), "result": "appended"})
        else:
            target.write_text(f["content"], encoding="utf-8")
            if exists:
                result["updated"] += 1
                result["details"].append({"path": str(f["target_path"]), "result": "updated"})
            else:
                result["created"] += 1
                result["details"].append({"path": str(f["target_path"]), "result": "created"})

    # Write audit log
    if not dry_run:
        audit_dir = vault_path / ".squirrel" / "applied"
        audit_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        short_hash = package["header"]["hash_sha256"][:8]
        audit_file = audit_dir / f"{ts}-{short_hash}.json"
        audit_data = {
            "applied_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "from": package["header"]["from"],
            "to": package["header"]["to"],
            "package_hash": package["header"]["hash_sha256"],
            "scope": package["header"]["scope"],
            "operations": result["details"],
        }
        audit_file.write_text(json.dumps(audit_data, indent=2), encoding="utf-8")
        result["audit_log"] = str(audit_file)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# GPG helpers
# ─────────────────────────────────────────────────────────────────────────────

def _gpg_available() -> bool:
    import shutil
    return shutil.which("gpg") is not None


def gpg_encrypt(content: str, recipient: str) -> bytes:
    """Encrypt a string to a GPG ASCII-armored ciphertext blob."""
    import subprocess
    try:
        result = subprocess.run(
            ["gpg", "--batch", "--yes", "--encrypt", "--armor", "--recipient", recipient],
            input=content.encode("utf-8"),
            capture_output=True,
        )
    except FileNotFoundError:
        raise RuntimeError("gpg not found in PATH")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def gpg_decrypt(ciphertext: bytes) -> str:
    """Decrypt a GPG-encrypted blob, return plaintext string."""
    import subprocess
    try:
        result = subprocess.run(
            ["gpg", "--batch", "--decrypt"],
            input=ciphertext,
            capture_output=True,
        )
    except FileNotFoundError:
        raise RuntimeError("gpg not found in PATH")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("utf-8")


def _read_gpg_recipient() -> str:
    """Read gpg_recipient from ~/.squirrel/config.toml, or return ''."""
    cfg = Path("~/.squirrel/config.toml").expanduser()
    if not cfg.exists():
        return ""
    for line in cfg.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("gpg_recipient"):
            return s.split("=", 1)[1].strip().strip("\"'")
    return ""


def cmd_generate(args):
    vault = Path(args.vault).expanduser().resolve()
    files = collect_files_by_scope(vault, args.scope)
    if not files:
        print(f"❌ No files matched scope: {args.scope}", file=sys.stderr)
        sys.exit(1)

    # Scan each for sensitive content
    for f in files:
        findings = scan_for_sensitive(f["content"])
        if findings:
            print(f"⚠️  {f['target_path']}: sensitive content detected:", file=sys.stderr)
            for line_num, name, snippet in findings:
                print(f"   line {line_num}: {name} — {snippet}", file=sys.stderr)
            print(f"   Aborting. Review or use --force-include.", file=sys.stderr)
            if not args.force_include:
                sys.exit(2)

    package = generate_package(
        files=files,
        from_env=args.from_env,
        to_env=args.to_env,
        scope=args.scope,
        intent=args.intent or "manual-export",
    )
    if getattr(args, "encrypt", False):
        recipient = getattr(args, "gpg_recipient", None) or _read_gpg_recipient()
        if not recipient:
            print("❌ --gpg-recipient required (or set gpg_recipient in config.toml)", file=sys.stderr)
            sys.exit(1)
        if not _gpg_available():
            print("❌ gpg not found in PATH", file=sys.stderr)
            sys.exit(1)
        try:
            encrypted = gpg_encrypt(package, recipient)
        except RuntimeError as e:
            print(f"❌ GPG encrypt failed: {e}", file=sys.stderr)
            sys.exit(1)
        out_path = Path(str(args.output) + ".gpg") if args.output else None
        if out_path:
            out_path.write_bytes(encrypted)
            print(f"✅ Encrypted package → {out_path}", file=sys.stderr)
        else:
            sys.stdout.buffer.write(encrypted)
    elif args.output:
        Path(args.output).write_text(package, encoding="utf-8")
        print(f"✅ Package written to {args.output}", file=sys.stderr)
    else:
        print(package)


def cmd_parse(args):
    content = Path(args.input).read_text(encoding="utf-8")
    try:
        package = parse_package(content)
        print(json.dumps(package, indent=2))
    except ValueError as e:
        print(f"❌ Parse error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_validate(args):
    content = Path(args.input).read_text(encoding="utf-8")
    try:
        package = parse_package(content)
    except ValueError as e:
        print(f"❌ Parse error: {e}", file=sys.stderr)
        sys.exit(1)

    valid, errors = validate_package(package)
    if valid:
        print("✅ Package is valid.")
        print(f"   From: {package['header']['from']}")
        print(f"   To:   {package['header']['to']}")
        print(f"   Files: {len(package['files'])}")
        print(f"   Hash: {package['header']['hash_sha256'][:16]}... ✓")
    else:
        print("❌ Package has errors:", file=sys.stderr)
        for err in errors:
            print(f"   • {err}", file=sys.stderr)
        sys.exit(1)


def cmd_apply(args):
    input_path = Path(args.input)
    if input_path.suffix == ".gpg" or getattr(args, "decrypt", False):
        if not _gpg_available():
            print("❌ gpg not found in PATH", file=sys.stderr)
            sys.exit(1)
        try:
            content = gpg_decrypt(input_path.read_bytes())
        except RuntimeError as e:
            print(f"❌ GPG decrypt failed: {e}", file=sys.stderr)
            sys.exit(1)
        print("🔓 Package decrypted.", file=sys.stderr)
    else:
        content = input_path.read_text(encoding="utf-8")
    try:
        package = parse_package(content)
    except ValueError as e:
        print(f"❌ Parse error: {e}", file=sys.stderr)
        sys.exit(1)

    valid, errors = validate_package(package)
    if not valid and not args.force_hash:
        print("❌ Package validation failed. Use --force-hash to override (NOT recommended).", file=sys.stderr)
        for err in errors:
            print(f"   • {err}", file=sys.stderr)
        sys.exit(1)

    vault = Path(args.vault).expanduser().resolve()
    result = apply_package(
        package,
        vault,
        dry_run=args.dry_run,
        interactive=not args.non_interactive,
    )

    print(f"\n{'(DRY RUN) ' if args.dry_run else ''}✅ Result:")
    print(f"   Created:  {result['created']}")
    print(f"   Updated:  {result['updated']}")
    print(f"   Skipped:  {result['skipped']}")
    print(f"   Failed:   {result['failed']}")
    if "audit_log" in result:
        print(f"   Audit log: {result['audit_log']}")


def main():
    parser = argparse.ArgumentParser(prog="package_protocol")
    subs = parser.add_subparsers(dest="cmd", required=True)

    g = subs.add_parser("generate", help="Generate a package from vault content")
    g.add_argument("--vault", required=True, help="Path to vault root")
    g.add_argument("--scope", required=True, help="Scope expression (TAG | PROJECT:* | PROJECT:research)")
    g.add_argument("--from-env", default="personal", dest="from_env")
    g.add_argument("--to-env", default="work", dest="to_env")
    g.add_argument("--intent", default="", help="Short description of why this package exists")
    g.add_argument("--output", help="Write package to file (default: stdout)")
    g.add_argument("--force-include", action="store_true", help="Include files even if sensitive content detected")
    g.add_argument("--encrypt", action="store_true", help="GPG-encrypt the output (requires gpg in PATH)")
    g.add_argument("--gpg-recipient", dest="gpg_recipient", metavar="EMAIL",
                   help="GPG recipient key ID or email (overrides config.toml gpg_recipient)")
    g.set_defaults(func=cmd_generate)

    p = subs.add_parser("parse", help="Parse a package, output JSON")
    p.add_argument("--input", required=True)
    p.set_defaults(func=cmd_parse)

    v = subs.add_parser("validate", help="Validate a package (hash, structure)")
    v.add_argument("--input", required=True)
    v.set_defaults(func=cmd_validate)

    a = subs.add_parser("apply", help="Apply a package to a vault")
    a.add_argument("--input", required=True)
    a.add_argument("--vault", required=True)
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--non-interactive", action="store_true", help="Don't prompt for conflicts (default: skip)")
    a.add_argument("--force-hash", action="store_true", help="Apply even with hash mismatch")
    a.add_argument("--decrypt", action="store_true", help="GPG-decrypt input before parsing (auto if .gpg extension)")
    a.set_defaults(func=cmd_apply)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
