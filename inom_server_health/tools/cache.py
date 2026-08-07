# -*- coding: utf-8 -*-
"""Process-local TTL cache with a single-flight guard.

Why this exists
---------------
Odoo runs N worker processes. Any counter kept in module memory is per-worker,
so this cache is deliberately NOT a source of truth -- it only stops the same
worker from recomputing an expensive metric on every poll.

The single-flight guard is the important part: if a collection is already
running, a concurrent request serves the stale value instead of queueing.
Without it, one slow `du` or one blocked PG query stacks up requests and eats
worker slots, which is exactly the failure mode this module must not cause.
"""

import threading
import time


class TTLCache:
    def __init__(self):
        self._values = {}
        self._locks = {}
        self._guard = threading.Lock()

    def _lock_for(self, key):
        with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = self._locks[key] = threading.Lock()
            return lock

    def get_or_set(self, key, ttl, producer, default=None):
        entry = self._values.get(key)
        now = time.monotonic()
        if entry is not None and (now - entry[0]) < ttl:
            return entry[1]

        lock = self._lock_for(key)
        if not lock.acquire(blocking=False):
            # Another thread is already refreshing. Never queue -- serve stale.
            return entry[1] if entry is not None else default
        try:
            value = producer()
            self._values[key] = (time.monotonic(), value)
            return value
        except Exception:
            # A broken probe must not break the whole payload.
            if entry is not None:
                # Push the timestamp forward so we don't retry on every poll.
                self._values[key] = (time.monotonic(), entry[1])
                return entry[1]
            self._values[key] = (time.monotonic(), default)
            return default
        finally:
            lock.release()

    def invalidate(self, key=None):
        if key is None:
            self._values.clear()
        else:
            self._values.pop(key, None)


CACHE = TTLCache()
