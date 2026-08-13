from typing import Protocol

from ...domain.environment import LocationQuery, RainfallLookup


class RainfallProvider(Protocol):
    def lookup(self, location: LocationQuery) -> RainfallLookup: ...
