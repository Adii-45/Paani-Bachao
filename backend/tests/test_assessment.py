from datetime import UTC, datetime

import pytest

from app.domain.environment import (
    RainfallLookup,
    RainfallRecord,
    RunoffCoefficientLookup,
    RunoffCoefficientRecord,
)
from app.provenance.models import (
    DataQuality,
    DataStatus,
    PublishedRange,
    ValueProvenance,
)
from app.schemas import AssessmentRequest
from app.services.assessment import create_assessment


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


def test_default_installation_returns_unavailable_without_demo_fallback() -> None:
    result = create_assessment(request())

    assert result.ruleset == "SOURCE_BACKED"
    assert result.isDemoData is False
    assert result.derived.rainfallStatus is DataStatus.DATA_UNAVAILABLE
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
    result = create_assessment(request(roofMaterial="RCC"))

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

    result = create_assessment(request(location="Published Example"))

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
        )
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
    result = create_assessment(request())
    ids = {source.source_id for source in result.sources}

    assert set(result.formula.sourceIds) <= ids
    assert set(result.rtrwh.sizingSourceIds) <= ids
    assert set(result.artificialRecharge.sourceIds) <= ids
