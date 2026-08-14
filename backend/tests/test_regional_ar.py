"""Golden tests for the intentionally limited production AR coverage.

Coordinates and expected environmental values are source-backed production-cache
records. Network geocoding is deliberately bypassed so CI remains deterministic;
the location resolver itself has separate mocked integration coverage.
"""

import pytest

from app.schemas import AssessmentRequest
from app.services.assessment import create_assessment


def assess(
    *, location: str, latitude: float, longitude: float, district: str, state: str,
    roof_area_m2: float = 100, open_area_m2: float = 10,
):
    return create_assessment(
        AssessmentRequest(
            location=location,
            latitude=latitude,
            longitude=longitude,
            district=district,
            state=state,
            roofAreaM2=roof_area_m2,
            roofMaterial="RCC",
            availableGroundAreaM2=open_area_m2,
            monthlyRainwaterDemandLitres=1_000,
            storageCapacityLitres=5_000,
            buildingHasBasement=False,
        )
    )


def test_hauz_khas_golden_flow_returns_partial_well_design_without_fake_depth() -> None:
    result = assess(
        location="Hauz Khas, Delhi",
        latitude=28.548,
        longitude=77.205,
        district="South Delhi",
        state="Delhi",
    )

    assert result.derived.annualRainfallMm == 809.0
    assert result.artificialRecharge.potentialRechargeLitresPerYear == 39_630
    assert result.artificialRecharge.feasibilityStatus == "CONDITIONALLY_ELIGIBLE"
    assert result.artificialRecharge.recommendedStructure.type == "TRENCH_WITH_RECHARGE_WELL"
    assert result.artificialRecharge.sizingStatus == "PARTIAL_INDICATIVE_DESIGN"
    assert result.artificialRecharge.dimensions["chamberDepthM"] == 0.5
    assert result.artificialRecharge.dimensions["finalWellTerminationDepthM"] is None
    assert "CGWB_DELHI_GWYB_2024_25" in result.artificialRecharge.sourceIds
    assert any("stale" in reason.casefold() for reason in result.artificialRecharge.reasons)
    groundwater = next(
        criterion
        for criterion in result.artificialRecharge.criteria
        if criterion.criterion == "groundwater_observation"
    )
    assert groundwater.result == "REQUIRES_VERIFICATION"
    assert result.artificialRecharge.environmentalProfile.soil.information is None
    assert any(
        "infiltration" in reason.casefold()
        for reason in result.artificialRecharge.fieldTestsRecommended
    )
    assert any(
        item.structure == "RECHARGE_TRENCH"
        and "15 m bgl" in item.reason
        for item in result.artificialRecharge.rejectedStructures
    )


def test_jayanagar_golden_flow_returns_karnataka_options_without_intake_depth() -> None:
    result = assess(
        location="Jayanagar, Bengaluru",
        latitude=12.916,
        longitude=77.58,
        district="Bengaluru Urban",
        state="Karnataka",
        roof_area_m2=1100 * 0.09290304,
        open_area_m2=100 * 0.09290304,
    )

    assert result.derived.annualRainfallMm == 822.1
    assert result.artificialRecharge.potentialRechargeLitresPerYear == 41_802.04
    assert result.artificialRecharge.feasibilityStatus == "CONDITIONALLY_ELIGIBLE"
    assert result.artificialRecharge.recommendedStructure.type == "RECHARGE_WELL"
    assert result.artificialRecharge.alternativeStructures == ["RECHARGE_PIT"]
    assert result.artificialRecharge.sizingMethodId == "KSCST_RESIDENTIAL_RWH_WELL_TABLE"
    assert result.artificialRecharge.dimensions["finalAquiferIntakeDepthM"] is None
    assert len(result.artificialRecharge.dimensions["wellOptions"]) == 3
    assert "CGWB_BENGALURU_NAQUIM_2025" in result.artificialRecharge.sourceIds
    assert "KSCST_RWH_TANK_WELL_SIZES" in result.artificialRecharge.sourceIds
    soil = result.artificialRecharge.environmentalProfile.soil.information
    assert soil.measured_infiltration_rate_mm_per_hr is None
    assert soil.infiltration_data_type.value == "REGIONAL_SOIL_PROXY"
    assert soil.field_test_recommended is True
    assert any("stale" in reason.casefold() for reason in result.artificialRecharge.reasons)
    water_quality = next(
        criterion
        for criterion in result.artificialRecharge.criteria
        if criterion.criterion == "water_quality_and_contamination_risk"
    )
    assert water_quality.result == "REQUIRES_VERIFICATION"


def test_missing_actual_tank_capacity_produces_no_fabricated_recharge_surplus() -> None:
    result = create_assessment(
        AssessmentRequest(
            location="Jayanagar, Bengaluru",
            latitude=12.916,
            longitude=77.58,
            district="Bengaluru Urban",
            state="Karnataka",
            roofAreaM2=100,
            roofMaterial="RCC",
            availableGroundAreaM2=10,
            monthlyRainwaterDemandLitres=1_000,
            buildingHasBasement=False,
        )
    )

    assert result.artificialRecharge.potentialRechargeLitresPerYear is None
    assert result.artificialRecharge.feasibilityStatus == "INSUFFICIENT_DATA"
    assert result.artificialRecharge.recommendedStructure is None


def test_missing_monthly_demand_produces_no_fabricated_recharge_surplus() -> None:
    result = create_assessment(
        AssessmentRequest(
            location="Jayanagar, Bengaluru",
            latitude=12.916,
            longitude=77.58,
            district="Bengaluru Urban",
            state="Karnataka",
            roofAreaM2=100,
            roofMaterial="RCC",
            availableGroundAreaM2=10,
            storageCapacityLitres=5_000,
            buildingHasBasement=False,
        )
    )

    assert result.artificialRecharge.potentialRechargeLitresPerYear is None
    assert result.artificialRecharge.quantityStatus == "INSUFFICIENT_DATA"
    assert result.artificialRecharge.recommendedStructure is None


def test_real_area_without_imported_rainfall_fails_safely() -> None:
    result = assess(
        location="Greater Kailash II, Delhi",
        latitude=28.534,
        longitude=77.247,
        district="South East Delhi",
        state="Delhi",
    )

    assert result.derived.annualRainfallMm is None
    assert result.rtrwh.potentialLitresPerYear is None
    assert result.artificialRecharge.potentialRechargeLitresPerYear is None
    assert result.artificialRecharge.recommendedStructure is None


@pytest.mark.parametrize(
    ("location", "latitude", "longitude", "district", "state"),
    [
        ("Indiranagar, Bengaluru", 12.9784, 77.6408, "Bengaluru Urban", "Karnataka"),
        ("Connaught Place, Delhi", 28.6315, 77.2167, "New Delhi", "Delhi"),
        ("Mumbai", 19.076, 72.8777, "Mumbai", "Maharashtra"),
        ("Chennai", 13.0827, 80.2707, "Chennai", "Tamil Nadu"),
        ("Hyderabad", 17.385, 78.4867, "Hyderabad", "Telangana"),
        ("Ajmer", 26.4499, 74.6399, "Ajmer", "Rajasthan"),
    ],
)
def test_locations_outside_reviewed_polygons_cannot_borrow_regional_methods(
    location: str,
    latitude: float,
    longitude: float,
    district: str,
    state: str,
) -> None:
    result = assess(
        location=location,
        latitude=latitude,
        longitude=longitude,
        district=district,
        state=state,
    )

    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.dimensions is None
    assert result.artificialRecharge.structureSelectionStatus in {
        "INSUFFICIENT_DATA_FOR_SELECTION",
        "UNSUPPORTED_LOCATION_FOR_SELECTION",
    }
    assert "CGWB_DELHI_STANDARD_DESIGNS" not in result.artificialRecharge.sourceIds
    assert "KSCST_RWH_TANK_WELL_SIZES" not in result.artificialRecharge.sourceIds
