from datetime import datetime

from pydantic import BaseModel

from .ar_environment import (
    AREnvironmentalProfile,
    GroundwaterLookup,
    HydrogeologyLookup,
    SoilLookup,
)
from .environment import RainfallLookup
from .location import LocationResolution


class EnvironmentalDataResult(BaseModel):
    """Provider-neutral environmental evidence collected for one location."""

    location_resolution: LocationResolution
    rainfall: RainfallLookup
    groundwater: GroundwaterLookup
    soil: SoilLookup
    hydrogeology: HydrogeologyLookup
    assembled_at: datetime

    def ar_profile(self) -> AREnvironmentalProfile | None:
        location = self.location_resolution.location
        if location is None:
            return None
        return AREnvironmentalProfile(
            location=location,
            groundwater=self.groundwater,
            soil=self.soil,
            hydrogeology=self.hydrogeology,
            assembledAt=self.assembled_at,
        )
