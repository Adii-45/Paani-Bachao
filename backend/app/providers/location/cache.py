from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Protocol

from ...domain.location import LocationResolution


class LocationResolutionCache(Protocol):
    def get(self, key: str) -> LocationResolution | None: ...

    def set(self, key: str, value: LocationResolution) -> None: ...


@dataclass(frozen=True)
class _CacheEntry:
    value: LocationResolution
    expires_at: float


class InMemoryLocationResolutionCache:
    """Bounded process-local TTL cache for normalized geocoder responses."""

    def __init__(
        self,
        *,
        ttl_seconds: float = 86_400,
        max_entries: int = 512,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Location cache TTL must be positive.")
        if max_entries <= 0:
            raise ValueError("Location cache size must be positive.")
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.clock = clock
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> LocationResolution | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self.clock():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return entry.value.model_copy(deep=True)

    def set(self, key: str, value: LocationResolution) -> None:
        with self._lock:
            self._entries[key] = _CacheEntry(
                value=value.model_copy(deep=True),
                expires_at=self.clock() + self.ttl_seconds,
            )
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
