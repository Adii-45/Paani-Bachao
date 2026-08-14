from typing import Protocol

from ..domain.ar_environment import (
    GroundwaterLookup,
    HydrogeologyLookup,
    SoilLookup,
)
from ..domain.location import NormalizedLocation


class GroundwaterProvider(Protocol):
    def lookup(self, location: NormalizedLocation) -> GroundwaterLookup: ...


class GeologyProvider(Protocol):
    def lookup(self, location: NormalizedLocation) -> HydrogeologyLookup: ...


class GeomorphologyProvider(Protocol):
    def lookup(self, location: NormalizedLocation) -> HydrogeologyLookup: ...


class SoilProvider(Protocol):
    def lookup(self, location: NormalizedLocation) -> SoilLookup: ...


class HydrogeologyProvider(Protocol):
    def lookup(self, location: NormalizedLocation) -> HydrogeologyLookup: ...
