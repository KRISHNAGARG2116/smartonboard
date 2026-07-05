import time
import threading

class AnalyticsCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            if key in self._cache:
                value, expires_at, tags = self._cache[key]
                if time.time() < expires_at:
                    return value
                else:
                    del self._cache[key]
            return None

    def set(self, key: str, value, ttl_seconds: int, tags: list[str] = None):
        with self._lock:
            self._cache[key] = (value, time.time() + ttl_seconds, tags or [])

    def invalidate_by_tag(self, tag: str):
        with self._lock:
            to_delete = []
            for key, (value, expires_at, tags) in self._cache.items():
                if tag in tags:
                    to_delete.append(key)
            for key in to_delete:
                self._cache.pop(key, None)

    def invalidate_company(self, company_id):
        cid_str = str(company_id)
        self.invalidate_by_tag(f"{cid_str}:dashboard")
        self.invalidate_by_tag(f"{cid_str}:funnel")

analytics_cache = AnalyticsCache()
