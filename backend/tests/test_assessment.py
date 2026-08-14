from datetime import UTC, date, datetime

import pytest

from app.domain.environment import (
    LocationQuery,
    RainfallLookup,
    RainfallRecord,
    MonthlyRainfallNormal,
    RunoffCoefficientLookup,
    RunoffCoefficientRecord,
)
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
from app.domain.location import (
    LocationResolution,
    LocationResolutionStatus,
    NormalizedLocation,
)
from app.provenance.models import (
    DataQuality,
    DataStatus,
    PublishedRange,
    ValueProvenance,
)
from app.providers.location.cache import InMemoryLocationResolutionCache
from app.providers.location.geocoding import NominatimLocationResolver
from app.schemas import AssessmentRequest
from app.services.assessment import create_assessment


class BengaluruResolver:
    def resolve(self, _query: LocationQuery) -> LocationResolution:
        return LocationResolution(
            status=LocationResolutionStatus.RESOLVED,
            location=NormalizedLocation(
                input="Bengaluru",
                canonicalName="Bengaluru, Karnataka, India",
                latitude=12.9716,
                longitude=77.5946,
                district="Bengaluru Urban",
                state="Karnataka",
                country="India",
                provider="test fixture",
                providerPlaceId="fixture-bengaluru",
                confidence="fixture",
            ),
            message="Resolved by deterministic test fixture.",
        )


class UnresolvedResolver:
    def resolve(self, _query: LocationQuery) -> LocationResolution:
        return LocationResolution(
            status=LocationResolutionStatus.NOT_RESOLVED,
            message="LocationNotResolved: deterministic test fixture.",
        )


class DelhiResolver:
    def resolve(self, _query: LocationQuery) -> LocationResolution:
        return LocationResolution(
            status=LocationResolutionStatus.RESOLVED,
            location=NormalizedLocation(
                input="Delhi",
                canonicalName="Delhi, India",
                latitude=28.6139,
                longitude=77.209,
                district="New Delhi",
                state="Delhi",
                country="India",
                provider="test fixture",
                providerPlaceId="fixture-delhi",
                confidence="fixture",
            ),
            message="Resolved by deterministic test fixture.",
        )


TEST_PROVENANCE = ValueProvenance(
    quality=DataQuality.AUTHORITATIVE_DATASET,
    sourceIds=["CGWB_DELHI_STANDARD_DESIGNS"],
    sourceRecord="deterministic integration fixture",
)


class DelhiGroundwaterProvider:
    def lookup(self, _location: NormalizedLocation) -> GroundwaterLookup:
        return GroundwaterLookup(
            status=DataStatus.DATA_AVAILABLE,
            observation=GroundwaterObservation(
                stationId="fixture-well",
                stationName="Fixture observation",
                depthBelowGroundLevelM=10,
                depthUnit="m bgl",
                observationDate=date(2025, 11, 15),
                season="POST_MONSOON",
                latitude=28.6139,
                longitude=77.209,
                district="New Delhi",
                state="Delhi",
                spatialResolution=EnvironmentalResolution.NEARBY_OBSERVATION,
                provenance=TEST_PROVENANCE,
            ),
            message="Deterministic nearby observation fixture.",
            recordCount=1,
        )


class UnavailableGroundwaterProvider:
    def lookup(self, _location: NormalizedLocation) -> GroundwaterLookup:
        return GroundwaterLookup(
            status=DataStatus.DATA_UNAVAILABLE,
            message="No deterministic groundwater observation is available.",
        )


class ShallowDelhiGroundwaterProvider(DelhiGroundwaterProvider):
    def lookup(self, location: NormalizedLocation) -> GroundwaterLookup:
        result = super().lookup(location)
        assert result.observation is not None
        return result.model_copy(
            update={
                "observation": result.observation.model_copy(
                    update={"depth_below_ground_level_m": 2.5}
                )
            }
        )


class DelhiSoilProvider:
    def lookup(self, _location: NormalizedLocation) -> SoilLookup:
        return SoilLookup(
            status=DataStatus.DATA_AVAILABLE,
            information=SoilInformation(
                recordId="fixture-soil",
                soilClass="field tested",
                measuredInfiltrationRateMmPerHr=10,
                infiltrationDataType=InfiltrationDataType.PROPERTY_MEASURED,
                spatialResolution=EnvironmentalResolution.PROPERTY_MEASURED,
                fieldTestRecommended=False,
                provenance=TEST_PROVENANCE,
            ),
            message="Deterministic property measurement fixture.",
        )


class RegionalDelhiSoilProvider:
    def lookup(self, _location: NormalizedLocation) -> SoilLookup:
        return SoilLookup(
            status=DataStatus.DATA_AVAILABLE,
            information=SoilInformation(
                recordId="fixture-regional-soil",
                soilClass="regional alluvial soil",
                measuredInfiltrationRateMmPerHr=None,
                infiltrationDataType=InfiltrationDataType.REGIONAL_SOIL_PROXY,
                spatialResolution=EnvironmentalResolution.REGIONAL_LAYER,
                fieldTestRecommended=True,
                provenance=TEST_PROVENANCE,
            ),
            message="Regional soil proxy fixture; field infiltration testing is required.",
        )


class DelhiHydrogeologyProvider:
    def lookup(self, _location: NormalizedLocation) -> HydrogeologyLookup:
        return HydrogeologyLookup(
            status=DataStatus.DATA_AVAILABLE,
            information=HydrogeologyInformation(
                recordId="fixture-hydrogeology",
                geology="Quaternary alluvial formation",
                lithology="alluvium",
                geomorphology="alluvial plain",
                groundwaterProspect="reviewed",
                aquiferType="unconfined alluvial aquifer",
                aquiferCharacteristics={"arMethodologyRegion": "DELHI_CGWB_STANDARD"},
                spatialResolution=EnvironmentalResolution.REGIONAL_LAYER,
                datasetVersion="deterministic fixture",
                provenance=TEST_PROVENANCE,
            ),
            geologyStatus=DataStatus.DATA_AVAILABLE,
            geomorphologyStatus=DataStatus.DATA_AVAILABLE,
            aquiferStatus=DataStatus.DATA_AVAILABLE,
            groundwaterProspectStatus=DataStatus.DATA_AVAILABLE,
            message="Deterministic intersecting hydrogeology fixture.",
        )


class DelhiRainfallProvider:
    def __init__(
        self,
        month_values: tuple[float, ...] | None = None,
    ) -> None:
        self.month_values = month_values or (
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            100.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )

    def lookup(self, _location: NormalizedLocation) -> RainfallLookup:
        annual_rainfall = sum(self.month_values)
        return RainfallLookup(
            status=DataStatus.DATA_AVAILABLE,
            record=RainfallRecord(
                recordId="fixture-rainfall",
                locationName="New Delhi",
                rainfallMm=annual_rainfall,
                statisticType="DETERMINISTIC_TEST_SERIES",
                referencePeriod="test fixture",
                spatialResolution="deterministic test fixture",
                sourceId="IMD_DISTRICT_ANNUAL_NORMALS_1971_2020",
                sourceName="India Meteorological Department (test-shaped fixture)",
                sourceUrl="https://www.imdpune.gov.in/climinfo/season/ann/index.html",
                sourceRecord="deterministic fixture; not a production rainfall record",
                datasetVersion="test fixture",
                retrievedAt=datetime(2026, 8, 13, tzinfo=UTC),
                monthlyNormal=MonthlyRainfallNormal(
                    valuesMm=self.month_values,
                    referencePeriod="test fixture",
                    spatialResolution="deterministic test fixture",
                    sourceId="IMD_DISTRICT_MONTHLY_NORMALS_1971_2020",
                    sourceName="India Meteorological Department (test-shaped fixture)",
                    sourceUrls=tuple("https://www.imdpune.gov.in" for _ in range(12)),
                    sourceRecords=tuple(f"fixture-{month}" for month in range(1, 13)),
                    datasetVersion="test fixture",
                    retrievedAt=datetime(2026, 8, 13, tzinfo=UTC),
                ),
            ),
            message="Deterministic rainfall fixture.",
        )


class UnavailableRainfallProvider:
    def lookup(self, _location: NormalizedLocation) -> RainfallLookup:
        return RainfallLookup(
            status=DataStatus.DATA_UNAVAILABLE,
            message="RainfallDataUnavailable: deterministic provider has no record.",
            errorCode="RAINFALL_DATA_UNAVAILABLE",
        )


def request(**overrides: object) -> AssessmentRequest:
    values: dict[str, object] = {
        "location": "Bengaluru",
        "roofAreaM2": 20,
        "roofMaterial": "OTHER",
        "soilType": "DONT_KNOW",
        "groundwaterDepthM": 8,
        "availableGroundAreaM2": 15,
    }
    values.update(overrides)
    return AssessmentRequest.model_validate(values)


def test_unresolved_location_returns_unavailable_without_demo_fallback() -> None:
    result = create_assessment(request(), location_resolver=UnresolvedResolver())

    assert result.ruleset == "SOURCE_BACKED"
    assert result.isDemoData is False
    assert result.derived.rainfallStatus is DataStatus.DATA_UNAVAILABLE
    assert result.derived.locationStatus is LocationResolutionStatus.NOT_RESOLVED
    assert result.derived.normalizedLocation is None
    assert result.derived.rainfall.errorCode == "LOCATION_NOT_RESOLVED"
    assert result.derived.annualRainfallMm is None
    assert result.derived.runoffCoefficient is None
    assert result.rtrwh.potentialLitresPerYear is None
    assert result.rtrwh.recommendedSizeLitres is None
    assert result.artificialRecharge.feasibilityStatus == "INSUFFICIENT_DATA"
    assert result.artificialRecharge.potentialRechargeLitresPerYear is None
    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.dimensions is None
    assert result.dataCompleteness == "INSUFFICIENT"
    assert all("demo" not in warning.casefold() for warning in result.warnings)


def test_source_backed_roof_coefficient_does_not_create_harvest_without_rainfall() -> None:
    result = create_assessment(
        request(roofMaterial="RCC"), location_resolver=UnresolvedResolver()
    )

    assert result.derived.runoffCoefficientStatus is DataStatus.DATA_AVAILABLE
    assert result.derived.runoffCoefficient == 0.7
    assert result.derived.runoffCoefficientEvidence.valueRange is not None
    assert result.derived.runoffCoefficientEvidence.valueRange.selection_method is not None
    assert result.rtrwh.potentialLitresPerYear is None


def test_published_cgwb_example_flows_through_assessment_with_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CGWB Manual (2007), §7.2.7.1, page 119: 1000×20×0.75=15000 L.

    The coefficient fixture reproduces the document example only. It is not enabled
    as a production default for any material.
    """

    rainfall = RainfallLookup(
        status=DataStatus.DATA_AVAILABLE,
        record=RainfallRecord(
            recordId="published-example-rainfall",
            locationName="Published Example",
            rainfallMm=1000,
            statisticType="LONG_PERIOD_NORMAL_ANNUAL",
            referencePeriod="CGWB worked example",
            spatialResolution="worked example; not a spatial dataset",
            sourceId="CGWB_MANUAL_AR_2007",
            sourceName="Central Ground Water Board (CGWB)",
            sourceUrl="https://cgwb.gov.in/sites/default/files/MainLinks/Manual-Artificial-Recharge.pdf",
            sourceRecord="§7.2.7.1 page 119",
            datasetVersion="2007",
            retrievedAt=datetime(2026, 8, 13, tzinfo=UTC),
        ),
        message="Published worked example.",
    )
    coefficient = RunoffCoefficientLookup(
        status=DataStatus.DATA_AVAILABLE,
        record=RunoffCoefficientRecord(
            roofType="OTHER",
            valueRange=PublishedRange(
                publishedMin=0.75,
                publishedMax=0.75,
                selectedValue=0.75,
                selectionMethod="Value used only in the cited CGWB worked example",
            ),
            condition="CGWB worked-example fixture; not a universal material value",
            sourceIds=["CGWB_MANUAL_AR_2007"],
            provenance=ValueProvenance(
                quality=DataQuality.ENGINEERING_DEFAULT,
                sourceIds=["CGWB_MANUAL_AR_2007"],
                sourceRecord="§7.2.7.1 page 119 worked example",
            ),
        ),
        message="Published worked-example coefficient.",
    )
    monkeypatch.setattr(
        "app.services.environmental_data.NormalizedImdRainfallProvider.lookup",
        lambda _self, _location: rainfall,
    )
    monkeypatch.setattr(
        "app.services.assessment.SourceBackedRunoffCoefficientProvider.lookup",
        lambda _self, _roof: coefficient,
    )

    result = create_assessment(
        request(location="Published Example"), location_resolver=BengaluruResolver()
    )

    assert result.formula.grossRainfallVolumeLitres == 20_000
    assert result.formula.estimatedLossesLitres == 5_000
    assert result.rtrwh.potentialLitresPerYear == 15_000
    assert result.formula.harvestableVolumeLitres == 15_000
    assert result.formula.methodId == "CGWB_MANUAL_2007_RTRWH_ANNUAL_VOLUME"
    assert result.formula.sourceIds == ["CGWB_MANUAL_AR_2007"]
    assert result.derived.rainfall.provenance is not None
    assert result.derived.rainfall.provenance.quality is DataQuality.AUTHORITATIVE_DATASET
    assert result.rtrwh.recommendedSizeLitres is None
    assert result.artificialRecharge.potentialRechargeLitresPerYear is None


def test_groundwater_metadata_is_preserved_but_does_not_hide_other_gaps() -> None:
    result = create_assessment(
        request(
            groundwaterObservationDate="2026-05-15",
            groundwaterObservationSeason="pre-monsoon",
            groundwaterObservationMethod="manual water-level measurement",
            groundwaterSource="user field observation",
        ),
        location_resolver=UnresolvedResolver(),
    )

    criterion = next(
        item
        for item in result.artificialRecharge.criteria
        if item.criterion == "groundwater_observation"
    )
    assert criterion.result == "REQUIRES_VERIFICATION"
    assert result.artificialRecharge.feasibilityStatus == "INSUFFICIENT_DATA"
    assert result.artificialRecharge.recommendedStructure is None


def test_all_returned_source_ids_resolve_to_registry_entries() -> None:
    result = create_assessment(request(), location_resolver=UnresolvedResolver())
    ids = {source.source_id for source in result.sources}

    assert set(result.formula.sourceIds) <= ids
    assert set(result.rtrwh.sizingSourceIds) <= ids
    assert set(result.artificialRecharge.sourceIds) <= ids


def test_location_to_imd_rainfall_to_rtrwh_integration() -> None:
    """IMD feature 43 rainfall + CGWB Table 7.2 concrete coefficient."""

    result = create_assessment(
        request(roofMaterial="RCC", roofAreaM2=20),
        location_resolver=BengaluruResolver(),
    )

    assert result.derived.locationStatus is LocationResolutionStatus.RESOLVED
    assert result.derived.normalizedLocation is not None
    assert result.derived.normalizedLocation.latitude == 12.9716
    assert result.derived.annualRainfallMm == 822.1
    assert result.derived.rainfall.referencePeriod == "1971-2020"
    assert result.derived.runoffCoefficient == 0.7
    assert result.formula.grossRainfallVolumeLitres == 16_442
    assert result.rtrwh.potentialLitresPerYear == 11_509.4


def test_realistic_location_string_resolves_into_environmental_pipeline() -> None:
    def geocoder_results(*_args: object) -> list[dict[str, object]]:
        return [
            {
                "place_id": 987,
                "display_name": (
                    "Indiranagar, Bengaluru, Bengaluru Urban, Karnataka, India"
                ),
                "lat": "12.9784",
                "lon": "77.6408",
                "importance": 0.61,
                "address": {
                    "suburb": "Indiranagar",
                    "city": "Bengaluru",
                    "state_district": "Bengaluru Urban",
                    "state": "Karnataka",
                    "postcode": "560038",
                    "country": "India",
                    "country_code": "in",
                },
            }
        ]

    resolver = NominatimLocationResolver(
        transport=geocoder_results,
        cache=InMemoryLocationResolutionCache(),
    )
    result = create_assessment(
        request(location="Indiranagar, Bengaluru", roofMaterial="RCC", roofAreaM2=20),
        location_resolver=resolver,
    )

    assert result.derived.locationStatus is LocationResolutionStatus.RESOLVED
    assert result.derived.normalizedLocation is not None
    assert result.derived.normalizedLocation.locality == "Indiranagar"
    assert result.derived.normalizedLocation.postalCode == "560038"
    assert result.derived.normalizedLocation.latitude == 12.9784
    assert result.derived.normalizedLocation.longitude == 77.6408
    assert result.derived.annualRainfallMm == 822.1
    assert result.artificialRecharge.environmentalProfile is not None
    assert result.artificialRecharge.environmentalProfile.location.latitude == 12.9784


def test_location_outside_original_city_set_resolves_into_rainfall_provider() -> None:
    def mysuru_geocoder(*_args: object) -> list[dict[str, object]]:
        return [
            {
                "place_id": 654,
                "display_name": "Mysuru, Mysore District, Karnataka, India",
                "lat": "12.2958",
                "lon": "76.6394",
                "importance": 0.59,
                "address": {
                    "city": "Mysuru",
                    "state_district": "Mysore",
                    "state": "Karnataka",
                    "postcode": "570001",
                    "country": "India",
                    "country_code": "in",
                },
            }
        ]

    result = create_assessment(
        request(location="Mysuru", roofMaterial="RCC", roofAreaM2=20),
        location_resolver=NominatimLocationResolver(
            transport=mysuru_geocoder,
            cache=InMemoryLocationResolutionCache(),
        ),
    )

    assert result.derived.locationStatus is LocationResolutionStatus.RESOLVED
    assert result.derived.normalizedLocation is not None
    assert result.derived.normalizedLocation.canonicalName.startswith("Mysuru")
    assert result.derived.normalizedLocation.postalCode == "570001"
    assert result.derived.annualRainfallMm == 760.4
    assert result.derived.rainfall.referencePeriod == "1971-2020"


def test_location_to_monthly_rainfall_demand_and_storage_integration() -> None:
    result = create_assessment(
        request(
            roofMaterial="RCC",
            roofAreaM2=20,
            monthlyRainwaterDemandLitres=500,
        ),
        location_resolver=BengaluruResolver(),
    )

    assert result.rtrwh.sizingStatus == "SIZE_AVAILABLE"
    assert result.rtrwh.recommendedSizeLitres == 5_538.8
    assert result.rtrwh.sizingRainfallReferencePeriod == "1971-2020"
    assert result.rtrwh.sizingRainfallResolution == (
        "IMD district monthly normal, 1971-2020"
    )
    assert result.rtrwh.demandUsedLitresPerMonth == 500
    assert result.rtrwh.estimatedSupplyLitres == 6_000
    assert result.rtrwh.demandMetPercent == 100
    assert len(result.rtrwh.storagePeriods) == 12
    assert len(result.rtrwh.sizingRainfallSourceRecords) == 12
    assert result.rtrwh.sizingMessage not in result.warnings
    source_ids = {source.source_id for source in result.sources}
    assert "IRICEN_RWH_2022" in source_ids
    assert "IMD_DISTRICT_MONTHLY_NORMALS_1971_2020" in source_ids


def test_rainfall_lookup_is_not_called_when_location_resolution_fails() -> None:
    class FailingRainfallProvider:
        def lookup(self, _location: NormalizedLocation) -> RainfallLookup:
            raise AssertionError("rainfall lookup must not run")

    result = create_assessment(
        request(),
        location_resolver=UnresolvedResolver(),
        rainfall_provider=FailingRainfallProvider(),
    )

    assert result.derived.rainfallStatus is DataStatus.DATA_UNAVAILABLE
    assert result.rtrwh.potentialLitresPerYear is None


def test_full_phase_one_flow_reaches_source_backed_ar_design() -> None:
    result = create_assessment(
        request(
            location="Delhi",
            roofAreaM2=100,
            roofMaterial="RCC",
            groundwaterDepthM=10,
            availableGroundAreaM2=10,
                monthlyRainwaterDemandLitres=1_000,
                storageCapacityLitres=5_000,
            buildingHasBasement=False,
            waterQualityStatus="VERIFIED_ACCEPTABLE",
            waterQualityEvidence="Deterministic qualified-review fixture",
        ),
        location_resolver=DelhiResolver(),
        rainfall_provider=DelhiRainfallProvider(),
        groundwater_provider=DelhiGroundwaterProvider(),
        soil_provider=DelhiSoilProvider(),
        hydrogeology_provider=DelhiHydrogeologyProvider(),
    )

    assert result.rtrwh.potentialLitresPerYear == 7_000
    assert result.rtrwh.estimatedOverflowLitres == 1_000
    assert result.artificialRecharge.potentialRechargeLitresPerYear == 1_000
    assert result.artificialRecharge.feasibilityStatus == "ELIGIBLE"
    assert result.artificialRecharge.recommendedStructure is not None
    assert result.artificialRecharge.recommendedStructure.type == "RECHARGE_TRENCH"
    assert result.artificialRecharge.dimensions == {
        "trenchLengthM": 1.2,
        "trenchWidthM": 1.2,
        "trenchDepthM": 1.4,
    }
    assert result.artificialRecharge.sizingStatus == "INDICATIVE_DESIGN_AVAILABLE"
    assert result.artificialRecharge.fieldVerificationRequired
    assert result.dataCompleteness == "GOOD"
    assert "CGWB_DELHI_STANDARD_DESIGNS" in result.artificialRecharge.sourceIds
    assert result.artificialRecharge.annualHarvestLitres is not None
    assert result.artificialRecharge.annualDemandSuppliedLitres is not None
    assert result.artificialRecharge.annualOverflowLitres is not None
    assert result.artificialRecharge.endingStorageLitres is not None
    assert result.artificialRecharge.annualHarvestLitres == pytest.approx(
        result.artificialRecharge.annualDemandSuppliedLitres
        + result.artificialRecharge.annualOverflowLitres
        + result.artificialRecharge.endingStorageLitres,
        abs=0.05,
    )
    assert 0 <= result.artificialRecharge.potentialRechargeLitresPerYear <= (
        result.rtrwh.potentialLitresPerYear
    )


def test_resolved_location_with_missing_rainfall_stops_rtrwh_and_ar_safely() -> None:
    result = create_assessment(
        request(
            location="Delhi",
            roofMaterial="RCC",
            monthlyRainwaterDemandLitres=1_000,
            storageCapacityLitres=5_000,
        ),
        location_resolver=DelhiResolver(),
        rainfall_provider=UnavailableRainfallProvider(),
        groundwater_provider=DelhiGroundwaterProvider(),
        soil_provider=DelhiSoilProvider(),
        hydrogeology_provider=DelhiHydrogeologyProvider(),
    )

    assert result.derived.rainfallStatus is DataStatus.DATA_UNAVAILABLE
    assert result.derived.annualRainfallMm is None
    assert result.rtrwh.potentialLitresPerYear is None
    assert result.rtrwh.recommendedSizeLitres is None
    assert result.artificialRecharge.potentialRechargeLitresPerYear is None
    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.dimensions is None


def test_missing_groundwater_keeps_rtrwh_but_blocks_ar_decision() -> None:
    result = create_assessment(
        request(
            location="Delhi",
            roofAreaM2=100,
            roofMaterial="RCC",
                monthlyRainwaterDemandLitres=1_000,
                storageCapacityLitres=5_000,
            buildingHasBasement=False,
            waterQualityStatus="VERIFIED_ACCEPTABLE",
            waterQualityEvidence="Deterministic qualified-review fixture",
        ),
        location_resolver=DelhiResolver(),
        rainfall_provider=DelhiRainfallProvider(),
        groundwater_provider=UnavailableGroundwaterProvider(),
        soil_provider=DelhiSoilProvider(),
        hydrogeology_provider=DelhiHydrogeologyProvider(),
    )

    assert result.rtrwh.potentialLitresPerYear == 7_000
    assert result.artificialRecharge.feasibilityStatus == "INSUFFICIENT_DATA"
    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.dimensions is None


def test_regional_infiltration_proxy_returns_conditional_with_field_test() -> None:
    result = create_assessment(
        request(
            location="Delhi",
            roofAreaM2=100,
            roofMaterial="RCC",
            monthlyRainwaterDemandLitres=1_000,
            storageCapacityLitres=5_000,
            buildingHasBasement=False,
            waterQualityStatus="VERIFIED_ACCEPTABLE",
            waterQualityEvidence="Deterministic qualified-review fixture",
        ),
        location_resolver=DelhiResolver(),
        rainfall_provider=DelhiRainfallProvider(),
        groundwater_provider=DelhiGroundwaterProvider(),
        soil_provider=RegionalDelhiSoilProvider(),
        hydrogeology_provider=DelhiHydrogeologyProvider(),
    )

    assert result.artificialRecharge.feasibilityStatus == "CONDITIONALLY_ELIGIBLE"
    assert result.artificialRecharge.fieldTestsRecommended
    assert any(
        "field" in reason.casefold()
        for reason in result.artificialRecharge.conditionsRequiringVerification
    )
    assert result.artificialRecharge.structureSelectionStatus == (
        "CONDITIONAL_RECOMMENDATION"
    )


def test_shallow_post_monsoon_groundwater_rejects_ar_without_structure() -> None:
    result = create_assessment(
        request(
            location="Delhi",
            roofAreaM2=100,
            roofMaterial="RCC",
            monthlyRainwaterDemandLitres=1_000,
            buildingHasBasement=False,
            waterQualityStatus="VERIFIED_ACCEPTABLE",
            waterQualityEvidence="Deterministic qualified-review fixture",
        ),
        location_resolver=DelhiResolver(),
        rainfall_provider=DelhiRainfallProvider(),
        groundwater_provider=ShallowDelhiGroundwaterProvider(),
        soil_provider=DelhiSoilProvider(),
        hydrogeology_provider=DelhiHydrogeologyProvider(),
    )

    assert result.artificialRecharge.feasibilityStatus == "NOT_ELIGIBLE"
    assert result.artificialRecharge.conditionsFailed
    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.dimensions is None


def test_full_flow_rejects_structure_when_site_footprint_is_too_small() -> None:
    result = create_assessment(
        request(
            location="Delhi",
            roofAreaM2=100,
            roofMaterial="RCC",
            availableGroundAreaM2=1,
            monthlyRainwaterDemandLitres=1_000,
            storageCapacityLitres=5_000,
            buildingHasBasement=False,
            waterQualityStatus="VERIFIED_ACCEPTABLE",
            waterQualityEvidence="Deterministic qualified-review fixture",
        ),
        location_resolver=DelhiResolver(),
        rainfall_provider=DelhiRainfallProvider(),
        groundwater_provider=DelhiGroundwaterProvider(),
        soil_provider=DelhiSoilProvider(),
        hydrogeology_provider=DelhiHydrogeologyProvider(),
    )

    assert result.artificialRecharge.structureSelectionStatus == (
        "NO_STRUCTURE_FITS_AVAILABLE_AREA"
    )
    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.rejectedStructures
    assert "exceeds" in result.artificialRecharge.rejectedStructures[-1].reason
    assert result.artificialRecharge.dimensions is None


def test_zero_storage_overflow_produces_no_positive_recharge_or_structure() -> None:
    result = create_assessment(
        request(
            location="Delhi",
            roofAreaM2=100,
            roofMaterial="RCC",
            monthlyRainwaterDemandLitres=1_000,
            storageCapacityLitres=100_000,
            buildingHasBasement=False,
            waterQualityStatus="VERIFIED_ACCEPTABLE",
            waterQualityEvidence="Deterministic qualified-review fixture",
        ),
        location_resolver=DelhiResolver(),
        rainfall_provider=DelhiRainfallProvider((100.0,) * 12),
        groundwater_provider=DelhiGroundwaterProvider(),
        soil_provider=DelhiSoilProvider(),
        hydrogeology_provider=DelhiHydrogeologyProvider(),
    )

    assert result.rtrwh.potentialLitresPerYear == 84_000
    assert result.rtrwh.estimatedOverflowLitres == 0
    assert result.artificialRecharge.potentialRechargeLitresPerYear == 0
    assert result.artificialRecharge.feasibilityStatus == "NOT_ELIGIBLE"
    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.dimensions is None
