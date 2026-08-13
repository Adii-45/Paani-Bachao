from typing import Protocol

from ..domain.environment import LocationQuery
from ..provenance.models import DataStatus


class EnvironmentalLookup(Protocol):
    status: DataStatus
    message: str


class GroundwaterProvider(Protocol):
    def lookup(self, location: LocationQuery) -> EnvironmentalLookup: ...


class GeologyProvider(Protocol):
    def lookup(self, location: LocationQuery) -> EnvironmentalLookup: ...


class GeomorphologyProvider(Protocol):
    def lookup(self, location: LocationQuery) -> EnvironmentalLookup: ...


class SoilProvider(Protocol):
    def lookup(self, location: LocationQuery) -> EnvironmentalLookup: ...
