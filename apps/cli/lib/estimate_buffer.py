#!/usr/bin/env python3
"""
estimate_buffer.py — Aplica el multiplicador de foco a estimaciones de tiempo.

Basado en Executive Function Toolkit: las estimaciones típicamente se
quedan cortas por factor 2-3×. Este script aplica el multiplicador apropiado
según el tamaño de la tarea.

Uso CLI:
    python3 estimate_buffer.py --minutes 30
    python3 estimate_buffer.py --hours 2.5
    python3 estimate_buffer.py --estimate "30 min"
    python3 estimate_buffer.py --estimate "2.5 hours"
"""

import argparse
import json
import re
import sys
from pathlib import Path


# Multiplier rules: (max_minutes, multiplier)
# Tasks <=5 min are notoriously underestimated
MULTIPLIER_RULES = [
    (5, 3.0),       # <=5 min → 3×
    (30, 3.0),      # 6-30 min → 3×
    (60, 2.5),      # 30-60 min → 2.5×
    (240, 2.0),     # 1-4h → 2×
    (480, 2.0),     # 4-8h → 2×
    (float("inf"), 1.5),  # >8h → 1.5×
]


def get_multiplier(minutes: float) -> float:
    """Return the appropriate multiplier for a given estimate."""
    for max_min, mult in MULTIPLIER_RULES:
        if minutes <= max_min:
            return mult
    return 1.5


def parse_estimate(s: str) -> float:
    """Parse a human estimate string. Returns minutes."""
    s = s.strip().lower()
    # Try matching "30 min", "2.5 h", "1.5 hours", "90 minutes"
    match = re.match(r"^(\d+\.?\d*)\s*(min|m|h|hr|hour|hours|minute|minutes)?$", s)
    if not match:
        raise ValueError(f"Cannot parse estimate: {s}")

    value = float(match.group(1))
    unit = (match.group(2) or "min").lower()

    if unit in ("h", "hr", "hour", "hours"):
        return value * 60
    return value  # assume minutes


def humanize_minutes(minutes: float) -> str:
    """Convert minutes to human-readable string."""
    if minutes < 60:
        return f"{int(minutes)} min"
    hours = minutes / 60
    if hours == int(hours):
        return f"{int(hours)}h"
    return f"{hours:.1f}h"


# @spec ATTN-003, ATTN-006, ATTN-013
def adjust_estimate(minutes: float) -> dict:
    """Apply focus multiplier and return structured info."""
    multiplier = get_multiplier(minutes)
    adjusted = minutes * multiplier

    return {
        "user_estimate_minutes": int(minutes),
        "user_estimate_human": humanize_minutes(minutes),
        "multiplier": multiplier,
        "adjusted_minutes": int(adjusted),
        "adjusted_human": humanize_minutes(adjusted),
        "explanation": _explain(minutes, multiplier),
    }


def _explain(minutes: float, multiplier: float) -> str:
    """Generate a human explanation of why this multiplier."""
    if minutes <= 30:
        return (
            "Tareas cortas (≤30 min) suelen tomar 3× más por context switch, "
            "setup mental, y subestimación del 'quick task'."
        )
    if minutes <= 60:
        return "Tareas de 30-60 min: 2.5× típicamente por scope creep y context switching."
    if minutes <= 240:
        return "Tareas de 1-4h: 2× por interrupciones y profundidad subestimada."
    if minutes <= 480:
        return "Día de trabajo (4-8h): 2× — un día 'completo' suele requerir 2 días."
    return "Tareas grandes (>8h): 1.5× — el error relativo se reduce con tareas mayores."


# ─────────────────────────────────────────────────────────────────────────────
# Estimate↔Actual reconciliation — persist an estimate onto an intent, and derive
# variance against tracked actual time. See docs/{hld,lld,ears}/
# estimate-actual-reconciliation.md.
#
# Persisted intent frontmatter keys (alongside the existing `time_invested_minutes`
# written by the focus checkout flow):
#   estimate_user_minutes  — raw user input (int minutes)
#   estimate_multiplier    — ADHD multiplier applied (float)
#   estimate_minutes       — adjusted estimate the user plans around (int minutes)
# Scope is `01-Active-Projects` only — the same scope where actuals are tracked
# and variance is displayed, so an estimate can never be set where it won't pay off.
# ─────────────────────────────────────────────────────────────────────────────

# @spec R-1.1..R-1.7, R-2.1, R-2.2, R-2.7, R-3.1..R-3.3, R-3.6, R-5.2, R-5.4

# Sane bounds for a single intent estimate (R-2.7). 6000 min = 100h.
MIN_ESTIMATE_MINUTES = 1
MAX_ESTIMATE_MINUTES = 6000

_ESTIMATE_KEYS = ("estimate_user_minutes", "estimate_multiplier", "estimate_minutes")


class EstimateError(Exception):
    """Raised when an estimate cannot be set (bad input or unresolvable intent)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _validate_minutes(minutes) -> float:
    """Coerce + bounds-check an estimate input (R-2.7)."""
    try:
        m = float(minutes)
    except (TypeError, ValueError):
        raise EstimateError("INVALID_MINUTES", "minutes must be numeric")
    if m <= 0 or m > MAX_ESTIMATE_MINUTES:
        raise EstimateError(
            "INVALID_MINUTES",
            f"minutes must be in (0, {MAX_ESTIMATE_MINUTES}]",
        )
    return m


def _coerce_num(value):
    """Tolerantly coerce a frontmatter scalar (always a string from the parser)
    to int. Returns None for missing/blank/non-numeric (R-3.6, R-5.2)."""
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _wip_intent_paths(vault_path: Path):
    """Yield every intent .md under 01-Active-Projects/*/ (Quick Tasks already
    excluded by find_intents_for_project — R-5.3, structural)."""
    sys.path.insert(0, str(Path(__file__).parent))
    from status_aggregator import find_intents_for_project, find_projects
    for project_md in find_projects(vault_path).get("wip", []):
        for intent_md in find_intents_for_project(project_md):
            yield intent_md


def resolve_wip_intent(vault_path, intent_id: str) -> Path:
    """Resolve an intent id to its file within active projects only (R-1.4).
    Raises EstimateError if not found in scope (R-1.5)."""
    for intent_md in _wip_intent_paths(Path(vault_path)):
        if intent_md.stem == intent_id:
            return intent_md
    raise EstimateError("INTENT_NOT_FOUND", f"intent not found in active projects: {intent_id}")


def _write_estimate(intent_path: Path, minutes) -> dict:
    """Write the three estimate keys atomically; leaves all other frontmatter
    (incl. time_invested_minutes) untouched (R-1.1, R-1.6, R-5.4)."""
    m = _validate_minutes(minutes)
    data = adjust_estimate(m)
    sys.path.insert(0, str(Path(__file__).parent))
    from intent_parser import write_frontmatter
    stored = {
        "estimate_user_minutes": data["user_estimate_minutes"],
        "estimate_multiplier": data["multiplier"],
        "estimate_minutes": data["adjusted_minutes"],
    }
    write_frontmatter(intent_path, dict(stored))
    return stored


def apply_estimate_to_intent(vault_path, intent_id: str, minutes) -> dict:
    """CLI path: resolve `intent_id` within active projects and persist (R-2.1)."""
    return _write_estimate(resolve_wip_intent(vault_path, intent_id), minutes)


def apply_estimate_by_slugs(vault_path, project_slug: str, intent_slug: str, minutes) -> dict:
    """API path: deterministic `01-Active-Projects/<project>/<intent>.md` (R-1.4)."""
    path = Path(vault_path) / "01-Active-Projects" / project_slug / f"{intent_slug}.md"
    if not path.is_file():
        raise EstimateError("INTENT_NOT_FOUND", f"intent not found: {project_slug}/{intent_slug}")
    return _write_estimate(path, minutes)


def clear_estimate_by_slugs(vault_path, project_slug: str, intent_slug: str) -> None:
    """Remove all three estimate keys in one atomic update (R-1.7)."""
    path = Path(vault_path) / "01-Active-Projects" / project_slug / f"{intent_slug}.md"
    if not path.is_file():
        raise EstimateError("INTENT_NOT_FOUND", f"intent not found: {project_slug}/{intent_slug}")
    sys.path.insert(0, str(Path(__file__).parent))
    from intent_parser import _DELETE, write_frontmatter
    write_frontmatter(path, {k: _DELETE for k in _ESTIMATE_KEYS})


def estimate_variance(frontmatter: dict) -> dict:
    """Derive estimate-vs-actual variance from an intent's frontmatter (read-side).
    Pure arithmetic, never raises; missing/malformed values are treated as absent
    (R-3.1, R-3.2, R-3.3, R-3.6)."""
    fm = frontmatter or {}
    est = _coerce_num(fm.get("estimate_minutes"))
    raw = _coerce_num(fm.get("estimate_user_minutes"))
    actual = _coerce_num(fm.get("time_invested_minutes"))

    out = {
        "estimate_minutes": est if (est and est > 0) else None,
        "estimate_user_minutes": raw if (raw and raw > 0) else None,
        "time_invested_minutes": actual if (actual and actual > 0) else None,
        "variance_minutes": None,
        "variance_ratio": None,
        "has_variance": False,
    }
    if out["estimate_minutes"] and out["time_invested_minutes"]:
        out["variance_minutes"] = out["time_invested_minutes"] - out["estimate_minutes"]
        out["variance_ratio"] = round(out["time_invested_minutes"] / out["estimate_minutes"], 2)
        out["has_variance"] = True
    return out


def main():
    p = argparse.ArgumentParser(prog="estimate_buffer")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--minutes", type=float)
    group.add_argument("--hours", type=float)
    group.add_argument("--estimate", help="Human string like '30 min' or '2.5 h'")
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    if args.minutes is not None:
        minutes = args.minutes
    elif args.hours is not None:
        minutes = args.hours * 60
    else:
        try:
            minutes = parse_estimate(args.estimate)
        except ValueError as e:
            print(f"❌ {e}", file=sys.stderr)
            sys.exit(1)

    result = adjust_estimate(minutes)
    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
