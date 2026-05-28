"""Tests for ATTN-004 and ATTN-012: chunk_helper threshold logic and next_physical_action."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from chunk_helper import chunk_task


# @spec ATTN-004, ATTN-012
def test_above_threshold_returns_phases_and_chunks():
    result = chunk_task(240)
    assert "phases" in result
    assert "sessions" in result
    assert result.get("below_threshold") is None


# @spec ATTN-004
def test_each_chunk_has_next_physical_action():
    result = chunk_task(240)
    for phase in result["phases"]:
        for chunk in phase["chunks"]:
            assert "next_physical_action" in chunk
            assert chunk["next_physical_action"].startswith("Start:")


# @spec ATTN-004
def test_at_threshold_returns_below_threshold():
    result = chunk_task(120)
    assert result == {"below_threshold": True, "threshold_minutes": 120, "total_minutes": 120}


# @spec ATTN-004
def test_below_threshold_returns_below_threshold():
    result = chunk_task(60)
    assert result["below_threshold"] is True
    assert result["total_minutes"] == 60
    assert result["threshold_minutes"] == 120


# @spec ATTN-004
def test_custom_threshold_respected_above():
    result = chunk_task(90, threshold_minutes=60)
    assert "phases" in result
    assert result.get("below_threshold") is None


# @spec ATTN-004
def test_custom_threshold_respected_below():
    result = chunk_task(30, threshold_minutes=60)
    assert result["below_threshold"] is True
    assert result["threshold_minutes"] == 60


# @spec ATTN-004, ATTN-012
def test_custom_phases_with_threshold_above():
    custom_phases = [
        {"name": "Alpha", "percent": 50, "emoji": "A"},
        {"name": "Beta", "percent": 50, "emoji": "B"},
    ]
    result = chunk_task(300, phases=custom_phases)
    assert "phases" in result
    phase_names = [p["name"] for p in result["phases"]]
    assert "Alpha" in phase_names
    assert "Beta" in phase_names


# @spec ATTN-004
def test_custom_phases_with_threshold_below():
    custom_phases = [
        {"name": "Alpha", "percent": 50, "emoji": "A"},
        {"name": "Beta", "percent": 50, "emoji": "B"},
    ]
    result = chunk_task(60, phases=custom_phases)
    assert result["below_threshold"] is True


SCRIPT = str(Path(__file__).parent.parent / "lib" / "chunk_helper.py")


# @spec ATTN-004, ATTN-012
def test_cli_hours_4_returns_valid_json():
    out = subprocess.check_output([sys.executable, SCRIPT, "--hours", "4"])
    data = json.loads(out)
    assert "phases" in data
    assert "sessions" in data


# @spec ATTN-004
def test_cli_hours_1_returns_below_threshold():
    out = subprocess.check_output([sys.executable, SCRIPT, "--hours", "1"])
    data = json.loads(out)
    assert data.get("below_threshold") is True
