#!/usr/bin/env python3
"""
estimate_buffer.py — Aplica el multiplicador ADHD a estimaciones de tiempo.

Basado en Executive Function Toolkit: las estimaciones ADHD típicamente se
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
    """Apply ADHD multiplier and return structured info."""
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
