"""
apps/backend/cache.py — process-local TTL cache for vault scans.

Implements R-9.8 (TTL cache), R-9.9 (write-path invalidation), and R-9.10
(observability) from docs/ears/phase-2-data-plane-and-desktop-popup.md
Unit 9. Designed to wrap aggregate_status / scan_vault_deadlines /
scan_vault_reminders inside server.py:api_home, which currently triggers
three full vault rglobs per /api/home request.

Stdlib only.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional


DEFAULT_TTL_SECONDS = 25.0


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    inserted_at: float


@dataclass
class _Stats:
    hits: int = 0
    misses: int = 0
    last_evicted_at: Optional[float] = None


_LOCK = threading.RLock()
_STORE: dict[tuple[str, str], CacheEntry] = {}
_STATS = _Stats()


def get_or_compute(
    vault_path: str,
    scan_kind: str,
    compute: Callable[[], Any],
    ttl: float = DEFAULT_TTL_SECONDS,
) -> Any:
    """Return cached value if fresh, else compute, store, and return.

    The compute callable runs outside the lock so a slow scan does not block
    other readers. Two concurrent misses on the same key may both call
    compute; whichever finishes last wins the store. The double-compute is
    acceptable given the cost of holding the lock for hundreds of ms.
    """
    key = (vault_path, scan_kind)
    now = time.monotonic()
    with _LOCK:
        entry = _STORE.get(key)
        if entry is not None and entry.expires_at > now:
            _STATS.hits += 1
            return entry.value
        _STATS.misses += 1
    value = compute()
    store_now = time.monotonic()
    with _LOCK:
        _STORE[key] = CacheEntry(
            value=value,
            expires_at=store_now + ttl,
            inserted_at=store_now,
        )
    return value


def invalidate(vault_path: str, scan_kind: Optional[str] = None) -> int:
    """Drop cache entries for vault_path.

    With scan_kind=None, drops every kind for that vault — the usual choice
    for write-path invalidation since a note write can affect any of the
    three scanners. Returns the number of entries evicted.
    """
    with _LOCK:
        if scan_kind is None:
            keys = [k for k in _STORE if k[0] == vault_path]
        else:
            keys = [k for k in _STORE if k == (vault_path, scan_kind)]
        for k in keys:
            del _STORE[k]
        if keys:
            _STATS.last_evicted_at = time.time()
        return len(keys)


def stats_snapshot() -> dict:
    """Return a JSON-safe snapshot for /api/cache/stats."""
    with _LOCK:
        total = _STATS.hits + _STATS.misses
        return {
            "entries": len(_STORE),
            "hits": _STATS.hits,
            "misses": _STATS.misses,
            "hit_rate": (_STATS.hits / total) if total else 0.0,
            "last_evicted_at": _STATS.last_evicted_at,
            "ttl_seconds": DEFAULT_TTL_SECONDS,
        }


def _reset_for_tests() -> None:
    """Clear store and stats. Test-only — not part of the public surface."""
    with _LOCK:
        _STORE.clear()
        _STATS.hits = 0
        _STATS.misses = 0
        _STATS.last_evicted_at = None
