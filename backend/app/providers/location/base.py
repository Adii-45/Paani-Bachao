from typing import Protocol

from ...domain.environment import LocationQuery
from ...domain.location import LocationResolution


class LocationResolver(Protocol):
    def resolve(self, query: LocationQuery) -> LocationResolution: ...
