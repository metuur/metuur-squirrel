#!/usr/bin/env python3
"""
Tests for ATTN-005 (deterministic focus score over a window) and
ATTN-008 (append-only switches.jsonl ledger).

Run: python3 -m pytest tests/test_attn_focus.py -v
"""

import json
import sys
import tempfile
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from switch_tracker import compute_focus_score_for_window, record_switch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


def _switches_log(vault: Path) -> Path:
    return vault / ".squirrel" / "switches.jsonl"


# ---------------------------------------------------------------------------
# ATTN-005: determinism + window
# ---------------------------------------------------------------------------

class TestATTN005:

    # @spec ATTN-005
    def test_same_input_same_score(self, tmp_path):
        vault = _vault(tmp_path)
        record_switch(vault, to_context="A", reason="voluntary")

        result1 = compute_focus_score_for_window(vault, "2020-01-01", "2099-12-31")
        result2 = compute_focus_score_for_window(vault, "2020-01-01", "2099-12-31")

        assert result1["focus_score"] == result2["focus_score"]

    # @spec ATTN-005
    def test_window_spanning_two_days(self, tmp_path):
        vault = _vault(tmp_path)
        log = _switches_log(vault)
        log.parent.mkdir(parents=True, exist_ok=True)

        entries = [
            {"timestamp": "2026-05-01T10:00:00+00:00", "date": "2026-05-01",
             "from": None, "to": "A", "reason": "voluntary"},
            {"timestamp": "2026-05-02T10:00:00+00:00", "date": "2026-05-02",
             "from": "A", "to": "B", "reason": "voluntary"},
        ]
        with log.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

        result = compute_focus_score_for_window(vault, "2026-05-01", "2026-05-02")
        assert result["switches"] == 2
        assert result["focus_score"] == 60  # 100 - 2*20

        only_day1 = compute_focus_score_for_window(vault, "2026-05-01", "2026-05-01")
        assert only_day1["switches"] == 1
        assert only_day1["focus_score"] == 80

    # @spec ATTN-005
    def test_empty_window_returns_100(self, tmp_path):
        vault = _vault(tmp_path)
        log = _switches_log(vault)
        log.parent.mkdir(parents=True, exist_ok=True)

        entry = {"timestamp": "2026-05-01T10:00:00+00:00", "date": "2026-05-01",
                 "from": None, "to": "A", "reason": "voluntary"}
        with log.open("w", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        result = compute_focus_score_for_window(vault, "2025-01-01", "2025-01-31")
        assert result["focus_score"] == 100
        assert result["switches"] == 0

    # @spec ATTN-005
    def test_session_start_only_returns_100(self, tmp_path):
        vault = _vault(tmp_path)
        record_switch(vault, to_context="A", reason="session-start")
        record_switch(vault, to_context="A", reason="session-end")

        result = compute_focus_score_for_window(vault, "2020-01-01", "2099-12-31")
        assert result["focus_score"] == 100

    # @spec ATTN-005
    def test_window_result_contains_required_keys(self, tmp_path):
        vault = _vault(tmp_path)
        result = compute_focus_score_for_window(vault, "2026-05-01", "2026-05-07")
        assert set(result.keys()) == {"from_date", "to_date", "switches", "focus_score"}
        assert result["from_date"] == "2026-05-01"
        assert result["to_date"] == "2026-05-07"


# ---------------------------------------------------------------------------
# ATTN-008: append-only ledger
# ---------------------------------------------------------------------------

class TestATTN008:

    # @spec ATTN-008
    def test_n_writes_produce_n_lines(self, tmp_path):
        vault = _vault(tmp_path)
        n = 5
        for i in range(n):
            record_switch(vault, to_context=f"ctx-{i}", reason="voluntary")

        log = _switches_log(vault)
        lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == n

    # @spec ATTN-008
    def test_first_line_unchanged_after_subsequent_write(self, tmp_path):
        vault = _vault(tmp_path)
        record_switch(vault, to_context="first", reason="voluntary")

        log = _switches_log(vault)
        first_line_before = log.read_text(encoding="utf-8").splitlines()[0]

        record_switch(vault, to_context="second", reason="voluntary")
        record_switch(vault, to_context="third", reason="voluntary")

        first_line_after = log.read_text(encoding="utf-8").splitlines()[0]
        assert first_line_before == first_line_after

    # @spec ATTN-008
    def test_concurrent_write_preserves_existing_lines(self, tmp_path):
        vault = _vault(tmp_path)
        record_switch(vault, to_context="initial", reason="session-start")

        log = _switches_log(vault)
        initial_content = log.read_bytes()

        errors = []

        def writer():
            try:
                for i in range(10):
                    record_switch(vault, to_context=f"w-{i}", reason="voluntary")
            except Exception as e:
                errors.append(e)

        thread = threading.Thread(target=writer)
        thread.start()
        thread.join()

        assert not errors
        content_after = log.read_bytes()
        assert content_after.startswith(initial_content)

    # @spec ATTN-008
    def test_no_truncation_across_multiple_sessions(self, tmp_path):
        vault = _vault(tmp_path)
        for batch in range(3):
            for i in range(2):
                record_switch(vault, to_context=f"b{batch}-c{i}", reason="voluntary")

        log = _switches_log(vault)
        lines = [l for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 6
        for line in lines:
            json.loads(line)
