from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from app.domain.ar_environment import (
    EnvironmentalResolution,
    GroundwaterLookup,
    GroundwaterObservation,
    HydrogeologyInformation,
    HydrogeologyLookup,
    InfiltrationDataType,
    SoilInformation,
    SoilLookup,
)
from app.domain.environment import (
    LocationQuery,
    MonthlyRainfallNormal,
    RainfallLookup,
    RainfallRecord,
)
from app.domain.location import (
    LocationResolution,
    LocationResolutionStatus,
    NormalizedLocation,
)
from app.provenance.models import DataQuality, DataStatus, ValueProvenance
from app.schemas import AssessmentRequest
from app.services.assessment import create_assessment
from app.services.environmental_data import EnvironmentalDataService


PROVENANCE = ValueProvenance(
    quality=DataQuality.AUTHORITATIVE_DATASET,
    sourceIds=["CGWB_MANUAL_AR_2007"],
    sourceRecord="deterministic Phase 2 integration fixture",
)


class FixtureResolver:
    def __init__(self, locations: dict[str, NormalizedLocation]) -> None:
        self.locations = locations

    def resolve(self, query: LocationQuery) -> LocationResolution:
        location = self.locations.get(query.location)
        if location is None:
            return LocationResolution(
                status=LocationResolutionStatus.NOT_RESOLVED,
                message="Fixture geocoder could not resolve the query.",
            )
        return LocationResolution(
            status=LocationResolutionStatus.RESOLVED,
            location=location,
            message="Resolved by deterministic geocoder fixture.",
        )


class FixtureRainfallProvider:
    def __init__(self, unsupported_longitudes: set[float] | None = None) -> None:
        self.unsupported_longitudes = unsupported_longitudes or set()
        self.seen: list[tuple[float, float]] = []

    def lookup(self, location: NormalizedLocation) -> RainfallLookup:
        self.seen.append((location.latitude, location.longitude))
        if location.longitude in self.unsupported_longitudes:
            return RainfallLookup(
                status=DataStatus.UNSUPPORTED_LOCATION,
                errorCode="RAINFALL_DATA_UNAVAILABLE",
                message="No imported rainfall polygon covers the coordinate.",
            )
        monthly = (100.0,) * 12
        return RainfallLookup(
            status=DataStatus.DATA_AVAILABLE,
            record=RainfallRecord(
                recordId=f"fixture-rainfall-{location.latitude}-{location.longitude}",
                locationName=location.canonical_name,
                state=location.state,
                district=location.district,
                rainfallMm=sum(monthly),
                statisticType="LONG_PERIOD_NORMAL_ANNUAL",
                referencePeriod="1971-2020 fixture shaped like imported IMD data",
                spatialResolution="district polygon fixture",
                sourceId="IMD_DISTRICT_ANNUAL_NORMALS_1971_2020",
                sourceName="India Meteorological Department",
                sourceUrl="https://www.imdpune.gov.in/climinfo/season/ann/index.html",
                sourceRecord="deterministic test fixture; not production data",
                datasetVersion="test fixture",
                retrievedAt=datetime(2026, 8, 14, tzinfo=UTC),
                monthlyNormal=MonthlyRainfallNormal(
                    valuesMm=monthly,
                    referencePeriod="1971-2020 fixture",
                    spatialResolution="district polygon fixture",
                    sourceId="IMD_DISTRICT_MONTHLY_NORMALS_1971_2020",
                    sourceName="India Meteorological Department",
                    sourceUrls=tuple("https://www.imdpune.gov.in" for _ in range(12)),
                    sourceRecords=tuple(f"fixture-month-{month}" for month in range(1, 13)),
                    datasetVersion="test fixture",
                    retrievedAt=datetime(2026, 8, 14, tzinfo=UTC),
                ),
            ),
            message="Coordinate matched an imported rainfall polygon fixture.",
        )


class FixtureGroundwaterProvider:
    def lookup(self, location: NormalizedLocation) -> GroundwaterLookup:
        return GroundwaterLookup(
            status=DataStatus.DATA_AVAILABLE,
            observation=GroundwaterObservation(
                stationId=f"well-{location.district}",
                stationName="Nearby fixture station",
                depthBelowGroundLevelM=10,
                depthUnit="m bgl",
                observationDate=date(2025, 11, 15),
                season="POST_MONSOON",
                latitude=location.latitude,
                longitude=location.longitude,
                district=location.district or "fixture district",
                state=location.state or "fixture state",
                distanceFromPropertyM=250,
                spatialResolution=EnvironmentalResolution.NEARBY_OBSERVATION,
                provenance=PROVENANCE,
            ),
            recordCount=1,
            message="Nearby observation fixture, not a property measurement.",
        )


class FixtureSoilProvider:
    def lookup(self, _location: NormalizedLocation) -> SoilLookup:
        return SoilLookup(
            status=DataStatus.DATA_AVAILABLE,
            information=SoilInformation(
                recordId="regional-soil-fixture",
                soilClass="mapped regional class",
                measuredInfiltrationRateMmPerHr=None,
                infiltrationDataType=InfiltrationDataType.REGIONAL_SOIL_PROXY,
                spatialResolution=EnvironmentalResolution.REGIONAL_LAYER,
                fieldTestRecommended=True,
                provenance=PROVENANCE,
            ),
            message="Regional soil proxy; field infiltration testing is required.",
        )


class FixtureHydrogeologyProvider:
    def lookup(self, _location: NormalizedLocation) -> HydrogeologyLookup:
        information = HydrogeologyInformation(
            recordId="hydrogeology-fixture",
            geology="mapped fixture geology",
            geomorphology="mapped fixture landform",
            groundwaterProspect="mapped fixture prospect",
            aquiferType="mapped fixture aquifer",
            spatialResolution=EnvironmentalResolution.REGIONAL_LAYER,
            datasetVersion="test fixture",
            provenance=PROVENANCE,
        )
        return HydrogeologyLookup(
            status=DataStatus.DATA_AVAILABLE,
            information=information,
            features=[information],
            geologyStatus=DataStatus.DATA_AVAILABLE,
            geomorphologyStatus=DataStatus.DATA_AVAILABLE,
            aquiferStatus=DataStatus.DATA_AVAILABLE,
            groundwaterProspectStatus=DataStatus.DATA_AVAILABLE,
            message="Mapped hydrogeological attributes are available.",
        )


class UnavailableGroundwaterProvider:
    def lookup(self, _location: NormalizedLocation) -> GroundwaterLookup:
        return GroundwaterLookup(
            status=DataStatus.DATA_UNAVAILABLE,
            message="No groundwater observation covers this coordinate.",
        )


class FailingGroundwaterProvider:
    def lookup(self, _location: NormalizedLocation) -> GroundwaterLookup:
        raise RuntimeError("simulated provider boundary failure")


class UnavailableSoilProvider:
    def lookup(self, _location: NormalizedLocation) -> SoilLookup:
        return SoilLookup(
            status=DataStatus.DATA_UNAVAILABLE,
            message="No soil polygon covers this coordinate.",
        )


class UnavailableHydrogeologyProvider:
    def lookup(self, _location: NormalizedLocation) -> HydrogeologyLookup:
        return HydrogeologyLookup(
            status=DataStatus.DATA_UNAVAILABLE,
            geologyStatus=DataStatus.DATA_UNAVAILABLE,
            geomorphologyStatus=DataStatus.DATA_UNAVAILABLE,
            aquiferStatus=DataStatus.DATA_UNAVAILABLE,
            groundwaterProspectStatus=DataStatus.DATA_UNAVAILABLE,
            message="No hydrogeology feature covers this coordinate.",
        )


class MustNotRunProvider:
    calls = 0

    def lookup(self, _location: NormalizedLocation) -> object:
        self.calls += 1
        raise AssertionError("Environmental provider must not run after geocoder failure.")


def location(
    name: str, latitude: float, longitude: float, district: str, state: str
) -> NormalizedLocation:
    return NormalizedLocation(
        input=name,
        canonicalName=f"{name}, {district}, {state}, India",
        latitude=latitude,
        longitude=longitude,
        locality=name,
        district=district,
        state=state,
        country="India",
        provider="deterministic geocoder fixture",
        providerPlaceId=f"fixture-{name.casefold()}",
        confidence="fixture",
    )


def request(place: str) -> AssessmentRequest:
    return AssessmentRequest(
        location=place,
        roofAreaM2=100,
        roofMaterial="RCC",
        soilType="DONT_KNOW",
        groundwaterDepthM=8,
        availableGroundAreaM2=15,
        monthlyRainwaterDemandLitres=2_000,
    )


def service(
    resolver: FixtureResolver,
    rainfall: FixtureRainfallProvider,
    *,
    groundwater: object | None = None,
    soil: object | None = None,
    hydrogeology: object | None = None,
) -> EnvironmentalDataService:
    return EnvironmentalDataService(
        location_resolver=resolver,
        rainfall_provider=rainfall,
        groundwater_provider=groundwater or FixtureGroundwaterProvider(),  # type: ignore[arg-type]
        soil_provider=soil or FixtureSoilProvider(),  # type: ignore[arg-type]
        hydrogeology_provider=hydrogeology or FixtureHydrogeologyProvider(),  # type: ignore[arg-type]
    )


def test_fully_supported_location_collects_each_provider_independently() -> None:
    place = "Dwarka Sector 6"
    resolver = FixtureResolver(
        {place: location(place, 28.5901, 77.0714, "South West Delhi", "Delhi")}
    )
    rainfall = FixtureRainfallProvider()

    result = create_assessment(
        request(place), environmental_data_service=service(resolver, rainfall)
    )

    assert result.environmentalData.rainfall.status is DataStatus.DATA_AVAILABLE
    assert result.environmentalData.groundwater.status is DataStatus.DATA_AVAILABLE
    assert result.environmentalData.soil.status is DataStatus.DATA_AVAILABLE
    assert result.environmentalData.hydrogeology.status is DataStatus.DATA_AVAILABLE
    assert result.environmentalData.hydrogeology.componentStatuses == {
        "geology": DataStatus.DATA_AVAILABLE,
        "geomorphology": DataStatus.DATA_AVAILABLE,
        "aquifer": DataStatus.DATA_AVAILABLE,
        "groundwaterProspect": DataStatus.DATA_AVAILABLE,
    }
    assert result.rtrwh.potentialLitresPerYear == pytest.approx(84_000)
    assert rainfall.seen == [(28.5901, 77.0714)]
    assert result.derived.rainfall.provenance is not None
    assert result.derived.rainfall.provenance.source_ids == [
        "IMD_DISTRICT_ANNUAL_NORMALS_1971_2020"
    ]
    profile = result.artificialRecharge.environmentalProfile
    assert profile is not None
    assert profile.groundwater.observation is not None
    assert profile.groundwater.observation.observation_date == date(2025, 11, 15)
    assert profile.soil.information is not None
    assert profile.soil.information.measured_infiltration_rate_mm_per_hr is None
    assert profile.soil.information.field_test_recommended is True
    assert profile.hydrogeology.information is not None
    assert profile.hydrogeology.information.groundwater_prospect == "mapped fixture prospect"


def test_rainfall_available_with_incomplete_ar_data_keeps_rtrwh_available() -> None:
    place = "Mysuru"
    resolver = FixtureResolver(
        {place: location(place, 12.2958, 76.6394, "Mysuru", "Karnataka")}
    )
    result = create_assessment(
        request(place),
        environmental_data_service=service(
            resolver,
            FixtureRainfallProvider(),
            groundwater=UnavailableGroundwaterProvider(),
            soil=UnavailableSoilProvider(),
            hydrogeology=UnavailableHydrogeologyProvider(),
        ),
    )

    assert result.rtrwh.potentialLitresPerYear == pytest.approx(84_000)
    assert result.rtrwh.calculationStatus is DataStatus.DATA_AVAILABLE
    assert result.environmentalData.rainfall.status is DataStatus.DATA_AVAILABLE
    assert result.environmentalData.groundwater.status is DataStatus.DATA_UNAVAILABLE
    assert result.environmentalData.soil.status is DataStatus.DATA_UNAVAILABLE
    assert result.environmentalData.hydrogeology.status is DataStatus.DATA_UNAVAILABLE
    assert result.artificialRecharge.feasibilityStatus in {
        "INSUFFICIENT_DATA",
        "NOT_ELIGIBLE",
    }
    assert result.artificialRecharge.recommendedStructure is None


def test_unsupported_rainfall_never_produces_rtrwh_result() -> None:
    place = "Port Blair"
    longitude = 92.7265
    resolver = FixtureResolver(
        {
            place: location(
                place, 11.6234, longitude, "South Andaman", "Andaman and Nicobar Islands"
            )
        }
    )
    result = create_assessment(
        request(place),
        environmental_data_service=service(
            resolver, FixtureRainfallProvider({longitude})
        ),
    )

    assert result.environmentalData.rainfall.status is DataStatus.UNSUPPORTED_LOCATION
    assert result.derived.annualRainfallMm is None
    assert result.rtrwh.potentialLitresPerYear is None
    assert result.formula.harvestableVolumeLitres is None


def test_one_provider_failure_does_not_discard_other_environmental_evidence() -> None:
    place = "Jaipur"
    resolver = FixtureResolver(
        {place: location(place, 26.9124, 75.7873, "Jaipur", "Rajasthan")}
    )
    result = create_assessment(
        request(place),
        environmental_data_service=service(
            resolver,
            FixtureRainfallProvider(),
            groundwater=FailingGroundwaterProvider(),
        ),
    )

    assert result.environmentalData.rainfall.status is DataStatus.DATA_AVAILABLE
    assert result.environmentalData.groundwater.status is DataStatus.PROVIDER_UNAVAILABLE
    assert result.environmentalData.soil.status is DataStatus.DATA_AVAILABLE
    assert result.environmentalData.hydrogeology.status is DataStatus.DATA_AVAILABLE
    assert result.rtrwh.potentialLitresPerYear == pytest.approx(84_000)
    assert result.artificialRecharge.environmentalProfile is not None


def test_geocoder_failure_skips_all_environmental_providers() -> None:
    resolver = FixtureResolver({})
    must_not_run = MustNotRunProvider()
    environmental_service = EnvironmentalDataService(
        location_resolver=resolver,
        rainfall_provider=must_not_run,  # type: ignore[arg-type]
        groundwater_provider=must_not_run,  # type: ignore[arg-type]
        soil_provider=must_not_run,  # type: ignore[arg-type]
        hydrogeology_provider=must_not_run,  # type: ignore[arg-type]
    )

    result = create_assessment(
        request("Unresolvable place"),
        environmental_data_service=environmental_service,
    )

    assert must_not_run.calls == 0
    assert result.environmentalData.locationStatus is LocationResolutionStatus.NOT_RESOLVED
    assert result.derived.annualRainfallMm is None
    assert result.rtrwh.potentialLitresPerYear is None
    assert result.artificialRecharge.environmentalProfile is None


@pytest.mark.parametrize(
    ("place", "latitude", "longitude", "district", "state"),
    [
        ("Mysuru", 12.2958, 76.6394, "Mysuru", "Karnataka"),
        ("Jaipur", 26.9124, 75.7873, "Jaipur", "Rajasthan"),
    ],
)
def test_locations_outside_original_five_use_coordinates_without_city_mapping(
    place: str,
    latitude: float,
    longitude: float,
    district: str,
    state: str,
) -> None:
    resolver = FixtureResolver(
        {place: location(place, latitude, longitude, district, state)}
    )
    rainfall = FixtureRainfallProvider()

    result = create_assessment(
        request(place), environmental_data_service=service(resolver, rainfall)
    )

    assert result.derived.normalizedLocation is not None
    assert result.derived.normalizedLocation.latitude == latitude
    assert result.derived.normalizedLocation.longitude == longitude
    assert rainfall.seen == [(latitude, longitude)]
    assert result.rtrwh.potentialLitresPerYear == pytest.approx(84_000)


def test_production_runtime_has_no_five_city_demo_rainfall_dependency() -> None:
    app_root = Path(__file__).resolve().parents[1] / "app"
    assert not (app_root / "data" / "demo").exists()
    assert not list((app_root / "data").rglob("rainfall.json"))

    production_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in app_root.rglob("*.py")
        if "__pycache__" not in path.parts
    )
    assert "data/demo" not in production_source
    assert "demo/rainfall" not in production_source


@pytest.mark.parametrize(
    ("place", "latitude", "longitude", "district", "state", "rainfall_mm"),
    [
        ("Mysuru", 12.2958, 76.6394, "Mysuru", "Karnataka", 760.4),
        ("Jaipur", 26.9124, 75.7873, "Jaipur", "Rajasthan", 588.0),
    ],
)
def test_real_imported_rainfall_cache_supports_locations_outside_original_five(
    place: str,
    latitude: float,
    longitude: float,
    district: str,
    state: str,
    rainfall_mm: float,
) -> None:
    payload = request(place).model_copy(
        update={
            "latitude": latitude,
            "longitude": longitude,
            "district": district,
            "state": state,
        }
    )

    result = create_assessment(payload)

    assert result.environmentalData.locationStatus is LocationResolutionStatus.RESOLVED
    assert result.environmentalData.rainfall.status is DataStatus.DATA_AVAILABLE
    assert result.derived.annualRainfallMm == rainfall_mm
    assert result.derived.rainfall.sourceName == "India Meteorological Department (IMD)"
    assert result.derived.rainfall.referencePeriod == "1971-2020"
    assert result.rtrwh.potentialLitresPerYear == pytest.approx(
        rainfall_mm * 100 * 0.70
    )
