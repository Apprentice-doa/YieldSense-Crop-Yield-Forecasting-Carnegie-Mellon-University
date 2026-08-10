"""Advisory cache.

The advisory fires once per season, so a cache is not a micro-optimisation: it
is what makes re-delivery (a farmer re-opening the app, an SMS resend, a retry
after a dropped 2G connection) free instead of billing another LLM call.

Key = payload hash + rules_version + lang. Consequences of that choice:

- A revised forecast changes the payload hash, so it misses cleanly and
  regenerates. No stale advice on a corrected number.
- A rules change bumps rules_version, invalidating everything it should.
- Each language is cached separately, because each is a separate generation.

Storage is in-process. Swapping in Redis means implementing get/set on this
interface -- REDIS_URL is already in .env.example.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional


def advisory_cache_key(
    payload_dict: Dict[str, Any], rules_version: str, lang: str
) -> str:
    """Stable key for one advisory.

    Sorted keys and a canonical separator so that dict ordering never changes
    the hash -- the same forecast must always produce the same key.
    """
    canonical = json.dumps(
        payload_dict, sort_keys=True, separators=(",", ":"), default=str
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
    return f"{digest}:{rules_version}:{lang}"


class AdvisoryCache:
    """Thread-safe TTL + LRU cache."""

    def __init__(self, ttl_seconds: int = 7776000, max_entries: int = 10000):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._store: "OrderedDict[str, tuple]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str, now: Optional[float] = None) -> Optional[Dict[str, Any]]:
        now = time.time() if now is None else now
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            stored_at, value = entry
            if now - stored_at > self.ttl:
                del self._store[key]
                self.misses += 1
                return None
            self._store.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Dict[str, Any], now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            self._store[key] = (now, value)
            self._store.move_to_end(key)
            while len(self._store) > self.max_entries:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "entries": len(self._store),
                "hits": self.hits,
                "misses": self.misses,
            }
