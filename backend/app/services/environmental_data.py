from datetime import UTC, datetime

from ..domain.ar_environment import (
    GroundwaterLookup,
    HydrogeologyLookup,
    SoilLookup,
)
from ..domain.environment import LocationQuery, RainfallLookup
from ..domain.environmental_data import EnvironmentalDataResult
from ..domain.location import (
    LocationResolution,
    LocationResolutionStatus,
    NormalizedLocation,
)
from ..provenance.models import DataStatus
from ..providers.environmental import (
    GroundwaterProvider,
    HydrogeologyProvider,
    SoilProvider,
)
from ..providers.groundwater import NormalizedCgwbGroundwaterProvider
from ..providers.hydrogeology import NormalizedOfficialHydrogeologyProvider
from ..providers.location import LocationResolver, NominatimLocationResolver
from ..providers.rainfall import NormalizedImdRainfallProvider
from ..providers.rainfall.base import RainfallProvider
from ..providers.soil import NormalizedOfficialSoilProvider


_PROVIDER_ERRORS = (OSError, RuntimeError, ValueError)


class EnvironmentalDataService:
    """Resolve a location and collect independent environmental evidence.

    Assessment calculations depend on this provider-neutral boundary rather than
    cache files, geocoder HTTP calls, or source-specific matching rules. A failed
    provider is isolated so it cannot fabricate data or erase evidence returned by
    another provider.
    """

    def __init__(
        self,
        *,
        location_resolver: LocationResolver | None = None,
        rainfall_provider: RainfallProvider | None = None,
        groundwater_provider: GroundwaterProvider | None = None,
        soil_provider: SoilProvider | None = None,
        hydrogeology_provider: HydrogeologyProvider | None = None,
    ) -> None:
        self.location_resolver = location_resolver or NominatimLocationResolver()
        self.rainfall_provider = rainfall_provider or NormalizedImdRainfallProvider()
        self.groundwater_provider = (
            groundwater_provider or NormalizedCgwbGroundwaterProvider()
        )
        self.soil_provider = soil_provider or NormalizedOfficialSoilProvider()
        self.hydrogeology_provider = (
            hydrogeology_provider or NormalizedOfficialHydrogeologyProvider()
        )

    def collect(self, query: LocationQuery) -> EnvironmentalDataResult:
        try:
            location_resolution = self.location_resolver.resolve(query)
        except _PROVIDER_ERRORS:
            location_resolution = LocationResolution(
                status=LocationResolutionStatus.PROVIDER_UNAVAILABLE,
                message="Location provider failed before a location could be resolved.",
            )

        location = location_resolution.location
        if (
            location_resolution.status is not LocationResolutionStatus.RESOLVED
            or location is None
        ):
            return self._location_unavailable(location_resolution)

        return EnvironmentalDataResult(
            location_resolution=location_resolution,
            rainfall=self._rainfall(location),
            groundwater=self._groundwater(location),
            soil=self._soil(location),
            hydrogeology=self._hydrogeology(location),
            assembled_at=datetime.now(UTC),
        )

    def _rainfall(self, location: NormalizedLocation) -> RainfallLookup:
        try:
            return self.rainfall_provider.lookup(location)
        except _PROVIDER_ERRORS:
            return RainfallLookup(
                status=DataStatus.PROVIDER_UNAVAILABLE,
                error_code="RAINFALL_DATA_UNAVAILABLE",
                message="Rainfall provider failed; no fallback rainfall was applied.",
            )

    def _groundwater(self, location: NormalizedLocation) -> GroundwaterLookup:
        try:
            return self.groundwater_provider.lookup(location)
        except _PROVIDER_ERRORS:
            return GroundwaterLookup(
                status=DataStatus.PROVIDER_UNAVAILABLE,
                message="Groundwater provider failed; no fallback depth was applied.",
            )

    def _soil(self, location: NormalizedLocation) -> SoilLookup:
        try:
            return self.soil_provider.lookup(location)
        except _PROVIDER_ERRORS:
            return SoilLookup(
                status=DataStatus.PROVIDER_UNAVAILABLE,
                message=(
                    "Soil provider failed; no soil class or infiltration value was inferred."
                ),
            )

    def _hydrogeology(self, location: NormalizedLocation) -> HydrogeologyLookup:
        try:
            return self.hydrogeology_provider.lookup(location)
        except _PROVIDER_ERRORS:
            return self._unavailable_hydrogeology(
                DataStatus.PROVIDER_UNAVAILABLE,
                "Hydrogeology provider failed; no subsurface attribute was inferred.",
            )

    @classmethod
    def _location_unavailable(
        cls, resolution: LocationResolution
    ) -> EnvironmentalDataResult:
        message = (
            "Environmental lookup was not attempted because the location was not resolved. "
            + resolution.message
        )
        return EnvironmentalDataResult(
            location_resolution=resolution,
            rainfall=RainfallLookup(
                status=DataStatus.DATA_UNAVAILABLE,
                error_code="LOCATION_NOT_RESOLVED",
                message="RainfallDataUnavailable: " + message,
            ),
            groundwater=GroundwaterLookup(
                status=DataStatus.DATA_UNAVAILABLE,
                message=message,
            ),
            soil=SoilLookup(status=DataStatus.DATA_UNAVAILABLE, message=message),
            hydrogeology=cls._unavailable_hydrogeology(
                DataStatus.DATA_UNAVAILABLE, message
            ),
            assembled_at=datetime.now(UTC),
        )

    @staticmethod
    def _unavailable_hydrogeology(
        status: DataStatus, message: str
    ) -> HydrogeologyLookup:
        return HydrogeologyLookup(
            status=status,
            features=[],
            geologyStatus=status,
            geomorphologyStatus=status,
            aquiferStatus=status,
            groundwaterProspectStatus=status,
            message=message,
        )
