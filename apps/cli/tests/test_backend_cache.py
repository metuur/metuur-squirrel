#!/usr/bin/env python3
"""
Unit tests for apps/backend/cache.py — the process-local TTL cache that
wraps the three vault scanners inside server.py:api_home.

Covers R-9.8 (TTL hit/miss), R-9.9 (write-path invalidation), and R-9.10
(observability) from docs/ears/phase-2-data-plane-and-desktop-popup.md
Unit 9.

Stdlib + unittest only — matches the rest of the suite under apps/cli/tests/.
"""

import pathlib
import sys
import threading
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
MONOREPO = REPO.parent.parent  # apps/cli → squirrel/
sys.path.insert(0, str(MONOREPO / "apps" / "backend"))


def _fresh_cache():
    """Reload cache between tests so stats and store start empty."""
    import cache
    cache._reset_for_tests()
    return cache


class GetOrComputeTests(unittest.TestCase):
    def setUp(self):
        self.cache = _fresh_cache()

    def test_first_call_computes_and_stores(self):
        calls = []

        def compute():
            calls.append(1)
            return {"value": 42}

        result = self.cache.get_or_compute("/vault/a", "status", compute)
        self.assertEqual(result, {"value": 42})
        self.assertEqual(len(calls), 1)
        stats = self.cache.stats_snapshot()
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["entries"], 1)

    def test_second_call_within_ttl_returns_cached(self):
        calls = []

        def compute():
            calls.append(1)
            return object()  # distinct identity each invocation

        first = self.cache.get_or_compute("/vault/a", "status", compute, ttl=60)
        second = self.cache.get_or_compute("/vault/a", "status", compute, ttl=60)

        self.assertIs(first, second)
        self.assertEqual(len(calls), 1)
        stats = self.cache.stats_snapshot()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertAlmostEqual(stats["hit_rate"], 0.5)

    def test_call_after_ttl_expires_recomputes(self):
        calls = []

        def compute():
            calls.append(1)
            return len(calls)

        # 0.05s TTL — fast enough to expire inside the test
        first = self.cache.get_or_compute("/vault/a", "status", compute, ttl=0.05)
        time.sleep(0.1)
        second = self.cache.get_or_compute("/vault/a", "status", compute, ttl=0.05)

        self.assertEqual(first, 1)
        self.assertEqual(second, 2)
        self.assertEqual(len(calls), 2)
        stats = self.cache.stats_snapshot()
        self.assertEqual(stats["misses"], 2)

    def test_different_keys_are_independent(self):
        self.cache.get_or_compute("/vault/a", "status", lambda: "A-status")
        self.cache.get_or_compute("/vault/a", "deadlines", lambda: "A-dl")
        self.cache.get_or_compute("/vault/b", "status", lambda: "B-status")
        self.assertEqual(self.cache.stats_snapshot()["entries"], 3)

    def test_compute_runs_outside_lock_so_concurrent_misses_dont_deadlock(self):
        # If compute ran inside _LOCK and re-entered get_or_compute, _LOCK is
        # an RLock so this would deadlock only on a non-reentrant lock. We
        # check the looser property: two threads doing independent misses
        # both return within a sane time budget.
        barrier = threading.Barrier(2)
        results = {}

        def worker(name, key):
            barrier.wait()

            def compute():
                time.sleep(0.05)
                return name

            results[name] = self.cache.get_or_compute("/vault/a", key, compute)

        t1 = threading.Thread(target=worker, args=("t1", "status"))
        t2 = threading.Thread(target=worker, args=("t2", "deadlines"))
        t1.start(); t2.start()
        t1.join(timeout=2); t2.join(timeout=2)
        self.assertFalse(t1.is_alive() or t2.is_alive(), "threads deadlocked")
        self.assertEqual(results, {"t1": "t1", "t2": "t2"})


class InvalidateTests(unittest.TestCase):
    def setUp(self):
        self.cache = _fresh_cache()

    def test_invalidate_one_kind(self):
        self.cache.get_or_compute("/vault/a", "status", lambda: "A1")
        self.cache.get_or_compute("/vault/a", "deadlines", lambda: "A2")
        evicted = self.cache.invalidate("/vault/a", "status")
        self.assertEqual(evicted, 1)
        # status recomputes, deadlines still cached
        self.assertEqual(
            self.cache.get_or_compute("/vault/a", "status", lambda: "A1-new"),
            "A1-new",
        )
        self.assertEqual(
            self.cache.get_or_compute("/vault/a", "deadlines", lambda: "ignored"),
            "A2",
        )

    def test_invalidate_whole_vault(self):
        self.cache.get_or_compute("/vault/a", "status", lambda: 1)
        self.cache.get_or_compute("/vault/a", "deadlines", lambda: 2)
        self.cache.get_or_compute("/vault/a", "reminders", lambda: 3)
        self.cache.get_or_compute("/vault/b", "status", lambda: 99)

        evicted = self.cache.invalidate("/vault/a")
        self.assertEqual(evicted, 3)
        # other vault is untouched
        self.assertEqual(
            self.cache.get_or_compute("/vault/b", "status", lambda: "ignored"),
            99,
        )
        stats = self.cache.stats_snapshot()
        self.assertIsNotNone(stats["last_evicted_at"])

    def test_invalidate_nonexistent_vault_is_noop(self):
        evicted = self.cache.invalidate("/vault/does-not-exist")
        self.assertEqual(evicted, 0)
        # last_evicted_at should NOT advance when nothing was dropped
        self.assertIsNone(self.cache.stats_snapshot()["last_evicted_at"])

    def test_write_then_immediate_read_returns_fresh_value(self):
        # End-to-end of the R-9.9 contract: a write handler invalidates,
        # the next read sees fresh data even though the prior TTL hasn't
        # elapsed.
        version = ["v1"]

        def compute():
            return version[0]

        self.assertEqual(self.cache.get_or_compute("/vault/a", "status", compute, ttl=60), "v1")
        version[0] = "v2"
        # Simulate a write happening
        self.cache.invalidate("/vault/a")
        self.assertEqual(self.cache.get_or_compute("/vault/a", "status", compute, ttl=60), "v2")


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.cache = _fresh_cache()

    def test_snapshot_shape(self):
        snap = self.cache.stats_snapshot()
        self.assertIn("entries", snap)
        self.assertIn("hits", snap)
        self.assertIn("misses", snap)
        self.assertIn("hit_rate", snap)
        self.assertIn("last_evicted_at", snap)
        self.assertIn("ttl_seconds", snap)
        self.assertEqual(snap["hit_rate"], 0.0)

    def test_hit_rate_climbs_toward_one_under_repeated_reads(self):
        for _ in range(10):
            self.cache.get_or_compute("/vault/a", "status", lambda: "x", ttl=60)
        snap = self.cache.stats_snapshot()
        # 1 miss + 9 hits = 0.9
        self.assertEqual(snap["misses"], 1)
        self.assertEqual(snap["hits"], 9)
        self.assertAlmostEqual(snap["hit_rate"], 0.9)


if __name__ == "__main__":
    unittest.main()
