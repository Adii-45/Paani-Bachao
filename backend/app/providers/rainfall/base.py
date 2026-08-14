from typing import Protocol

from ...domain.environment import RainfallLookup
from ...domain.location import NormalizedLocation


class RainfallProvider(Protocol):
    def lookup(self, location: NormalizedLocation) -> RainfallLookup: ...
