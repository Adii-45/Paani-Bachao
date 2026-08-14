from datetime import UTC, datetime

import pytest

from app.domain.environment import (
    LocationQuery,
    RainfallLookup,
    RainfallRecord,
    RunoffCoefficientLookup,
    RunoffCoefficientRecord,
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
        "app.services.assessment.NormalizedImdRainfallProvider.lookup",
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
    assert criterion.result == "DATA_AVAILABLE"
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
