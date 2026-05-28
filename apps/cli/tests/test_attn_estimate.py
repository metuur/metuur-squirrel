import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import estimate_buffer as eb


# --- ATTN-003 / ATTN-006: contract keys always present ---

# @spec ATTN-003, ATTN-006
def test_adjust_estimate_has_required_keys():
    result = eb.adjust_estimate(30)
    assert "user_estimate_human" in result
    assert "multiplier" in result
    assert "adjusted_human" in result


# @spec ATTN-003, ATTN-006
def test_adjust_estimate_keys_present_for_all_ranges():
    for minutes in [5, 30, 60, 120, 300, 600]:
        result = eb.adjust_estimate(minutes)
        assert "user_estimate_human" in result, f"missing user_estimate_human for {minutes}m"
        assert "multiplier" in result, f"missing multiplier for {minutes}m"
        assert "adjusted_human" in result, f"missing adjusted_human for {minutes}m"


# --- Multiplier bounds ---

# @spec ATTN-003
def test_multiplier_within_spec_bounds():
    for minutes in [1, 5, 15, 30, 60, 120, 240, 480, 600]:
        m = eb.get_multiplier(minutes)
        assert 1.5 <= m <= 3.0, f"multiplier {m} out of [1.5, 3.0] for {minutes}m"


# --- Raw estimate matches input ---

# @spec ATTN-006
def test_raw_estimate_matches_input():
    result = eb.adjust_estimate(45)
    assert result["user_estimate_minutes"] == 45
    assert result["user_estimate_human"] == "45 min"


# @spec ATTN-006
def test_raw_estimate_hours():
    result = eb.adjust_estimate(120)
    assert result["user_estimate_minutes"] == 120
    assert result["user_estimate_human"] == "2h"


# --- Buffered estimate equals raw × multiplier ---

# @spec ATTN-003, ATTN-006
def test_adjusted_matches_raw_times_multiplier():
    for minutes in [10, 30, 60, 90, 180, 480]:
        result = eb.adjust_estimate(minutes)
        expected = int(minutes * result["multiplier"])
        assert result["adjusted_minutes"] == expected, (
            f"adjusted_minutes {result['adjusted_minutes']} != {minutes} * {result['multiplier']}"
        )


# --- parse_estimate handles required formats ---

def test_parse_estimate_minutes_suffix():
    assert eb.parse_estimate("30 min") == 30.0


def test_parse_estimate_hours_suffix():
    assert eb.parse_estimate("2h") == 120.0


def test_parse_estimate_hours_long():
    assert eb.parse_estimate("1.5 hours") == 90.0


def test_parse_estimate_bare_number_is_minutes():
    assert eb.parse_estimate("90") == 90.0


def test_parse_estimate_minutes_long():
    assert eb.parse_estimate("45 minutes") == 45.0


# --- Script exits non-zero on unparseable input ---

def test_script_exits_nonzero_on_bad_input():
    script = Path(__file__).parent.parent / "lib" / "estimate_buffer.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--estimate", "not-a-time"],
        capture_output=True,
    )
    assert proc.returncode != 0


def test_parse_estimate_raises_on_bad_input():
    try:
        eb.parse_estimate("not-a-time")
        assert False, "should have raised ValueError"
    except ValueError:
        pass
