#!/usr/bin/env python3
"""
chunk_helper.py — Sugiere estructura de fases para chunking ADHD-friendly.

Toma una estimación en horas/minutos y devuelve la estructura de fases
con distribución de tiempo. El LLM toma esto y le pone nombres específicos
al dominio del intent.

Reglas:
  - Cada chunk: ≤60 min (idealmente 30-45)
  - Sesiones de hyperfocus: ≤3 horas
  - Distribución por fases: Research 15% / Setup 20% / Core 40% / Polish 15% / Test 10%

Uso CLI:
    python3 chunk_helper.py --hours 8
    python3 chunk_helper.py --minutes 240
    python3 chunk_helper.py --hours 8 --custom-phases research=20,core=50,test=30
"""

import argparse
import json
import sys


# Default phase distribution (must sum to 100)
DEFAULT_PHASES = [
    {"name": "Research & Planning", "percent": 15, "emoji": "🔬"},
    {"name": "Setup & Scaffolding", "percent": 20, "emoji": "🛠"},
    {"name": "Core Implementation", "percent": 40, "emoji": "⚙️"},
    {"name": "Polish & Edge Cases", "percent": 15, "emoji": "✨"},
    {"name": "Testing & Documentation", "percent": 10, "emoji": "🧪"},
]

MAX_CHUNK_MINUTES = 50
MAX_SESSION_MINUTES = 180  # 3h max hyperfocus session


def parse_custom_phases(spec: str) -> list[dict]:
    """Parse 'name1=N1,name2=N2,...' format."""
    phases = []
    for part in spec.split(","):
        if "=" not in part:
            raise ValueError(f"Bad phase spec: {part}")
        name, _, pct = part.partition("=")
        phases.append({
            "name": name.strip().title(),
            "percent": int(pct.strip()),
            "emoji": "📌",
        })
    total = sum(p["percent"] for p in phases)
    if total != 100:
        raise ValueError(f"Phase percents must sum to 100, got {total}")
    return phases


# @spec ATTN-004, ATTN-012
def chunk_task(total_minutes: int, phases: list[dict] = None, threshold_minutes: int = 120) -> dict:
    """Decompose a task into phases and chunks."""
    if total_minutes <= threshold_minutes:
        return {
            "below_threshold": True,
            "threshold_minutes": threshold_minutes,
            "total_minutes": total_minutes,
        }

    if phases is None:
        phases = DEFAULT_PHASES

    all_chunks = []
    phase_outputs = []

    for phase in phases:
        phase_minutes = int(total_minutes * phase["percent"] / 100)
        if phase_minutes == 0:
            continue

        # Split phase into chunks of MAX_CHUNK_MINUTES
        n_chunks = max(1, (phase_minutes + MAX_CHUNK_MINUTES - 1) // MAX_CHUNK_MINUTES)
        chunk_minutes = phase_minutes // n_chunks

        phase_chunks = []
        for i in range(n_chunks):
            is_last = (i == n_chunks - 1)
            chunk = {
                "phase": phase["name"],
                "chunk_number": f"{i + 1}/{n_chunks}",
                "minutes": chunk_minutes,
                "emoji": phase["emoji"],
                "dopamine_reward": "✅" if is_last else "⏭️",
                "placeholder_name": f"{phase['name']} ({i + 1}/{n_chunks})",
                "next_physical_action": f"Start: {phase['name']} ({i + 1}/{n_chunks})",
            }
            phase_chunks.append(chunk)
            all_chunks.append(chunk)

        phase_outputs.append({
            "name": phase["name"],
            "emoji": phase["emoji"],
            "percent": phase["percent"],
            "total_minutes": phase_minutes,
            "n_chunks": n_chunks,
            "chunks": phase_chunks,
        })

    # Group chunks into hyperfocus sessions (≤MAX_SESSION_MINUTES each)
    sessions = []
    current_session = {"id": 1, "chunks": [], "total_minutes": 0}
    session_id = 1

    for chunk in all_chunks:
        if current_session["total_minutes"] + chunk["minutes"] > MAX_SESSION_MINUTES:
            if current_session["chunks"]:
                sessions.append(current_session)
            session_id += 1
            current_session = {"id": session_id, "chunks": [], "total_minutes": 0}

        current_session["chunks"].append(chunk)
        current_session["total_minutes"] += chunk["minutes"]

    if current_session["chunks"]:
        sessions.append(current_session)

    return {
        "total_minutes": total_minutes,
        "total_human": f"{total_minutes // 60}h {total_minutes % 60}min" if total_minutes >= 60 else f"{total_minutes}min",
        "phases": phase_outputs,
        "total_chunks": len(all_chunks),
        "sessions": sessions,
        "estimated_days": max(1, len(sessions) // 2),  # ~2 sessions per day max
    }


def main():
    p = argparse.ArgumentParser(prog="chunk_helper")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--minutes", type=int)
    group.add_argument("--hours", type=float)
    p.add_argument("--custom-phases", help="Format: name1=N,name2=M (sum=100)")
    p.add_argument("--threshold", type=int, default=120, help="Min minutes before chunking kicks in (default: 120)")
    p.add_argument("--pretty", action="store_true")
    args = p.parse_args()

    if args.minutes:
        total = args.minutes
    else:
        total = int(args.hours * 60)

    phases = None
    if args.custom_phases:
        try:
            phases = parse_custom_phases(args.custom_phases)
        except ValueError as e:
            print(f"❌ {e}", file=sys.stderr)
            sys.exit(1)

    result = chunk_task(total, phases=phases, threshold_minutes=args.threshold)
    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
