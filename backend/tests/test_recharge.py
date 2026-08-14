import pytest

from app.engineering.recharge.feasibility import (
    CriterionStatus,
    FeasibilityStatus,
    WaterQualityStatus,
    evaluate_feasibility,
)
from app.engineering.recharge.quantity import (
    RechargeQuantityStatus,
    assess_recharge_quantity,
)
from app.engineering.recharge.sizing import assess_structure_size
from app.engineering.recharge.structure_selection import select_structure


def feasibility(**overrides: object):
    values: dict[str, object] = {
        "groundwater_depth_m_bgl": 10,
        "groundwater_has_observation_metadata": True,
        "groundwater_observation_season": "POST_MONSOON",
        "recharge_water_litres": 5_000,
        "has_infiltration_evidence": True,
        "infiltration_is_property_measured": True,
        "has_hydrogeology_evidence": True,
        "water_quality_status": WaterQualityStatus.VERIFIED_ACCEPTABLE,
        "available_ground_area_m2": 15,
    }
    values.update(overrides)
    return evaluate_feasibility(**values)  # type: ignore[arg-type]


def test_storage_overflow_is_available_recharge_water_without_fraction() -> None:
    result = assess_recharge_quantity(
        annual_harvest_litres=1_000,
        annual_demand_supplied_litres=600,
        annual_overflow_litres=300,
        catchment_losses_litres=200,
        ending_storage_litres=100,
    )

    assert result.status is RechargeQuantityStatus.DATA_AVAILABLE
    assert result.potential_recharge_litres_per_year == 300
    assert result.annual_demand_supplied_litres == 600
    assert result.catchment_losses_litres == 200
    assert "overflow" in result.assumptions[0].casefold()


def test_all_harvest_used_or_retained_produces_no_recharge_surplus() -> None:
    result = assess_recharge_quantity(
        annual_harvest_litres=1_000,
        annual_demand_supplied_litres=900,
        annual_overflow_litres=0,
        ending_storage_litres=100,
    )

    assert result.status is RechargeQuantityStatus.NO_RECHARGE_SURPLUS
    assert result.potential_recharge_litres_per_year == 0


def test_recharge_quantity_requires_complete_conserved_balance() -> None:
    incomplete = assess_recharge_quantity()
    assert incomplete.status is RechargeQuantityStatus.INSUFFICIENT_DATA
    assert incomplete.potential_recharge_litres_per_year is None

    with pytest.raises(ValueError, match="not conserved"):
        assess_recharge_quantity(
            annual_harvest_litres=1_000,
            annual_demand_supplied_litres=500,
            annual_overflow_litres=600,
            ending_storage_litres=0,
        )


def test_post_monsoon_water_shallower_than_three_metres_is_not_eligible() -> None:
    result = feasibility(groundwater_depth_m_bgl=2.9)
    groundwater = next(c for c in result.criteria if c.criterion == "groundwater_observation")

    assert result.status is FeasibilityStatus.NOT_ELIGIBLE
    assert groundwater.result is CriterionStatus.FAILED
    assert "shallower than 3 m" in groundwater.reason


def test_missing_hydrogeology_is_insufficient_not_scored() -> None:
    result = feasibility(has_hydrogeology_evidence=False)

    assert result.status is FeasibilityStatus.INSUFFICIENT_DATA
    assert not hasattr(result, "score")
    assert any("hydrogeological" in reason for reason in result.missing_data)


def test_unverified_infiltration_and_quality_create_explicit_conditions() -> None:
    result = feasibility(
        has_infiltration_evidence=False,
        infiltration_is_property_measured=False,
        water_quality_status=WaterQualityStatus.NOT_VERIFIED,
    )

    assert result.status is FeasibilityStatus.CONDITIONALLY_ELIGIBLE
    assert len(result.conditions_requiring_verification) == 2
    assert any("field test" in item for item in result.field_tests_recommended)


def test_all_explicit_conditions_satisfied_is_eligible() -> None:
    result = feasibility()
    assert result.status is FeasibilityStatus.ELIGIBLE
    assert result.conditions_failed == ()
    assert result.missing_data == ()


def test_delhi_alluvial_site_selects_trench_from_published_conditions() -> None:
    result = select_structure(
        feasibility(),
        state="Delhi",
        geology="Quaternary alluvium",
        groundwater_depth_m_bgl=10,
        building_has_basement=False,
        roof_area_m2=120,
        available_ground_area_m2=10,
    )

    assert result.status == "RECOMMENDED"
    assert result.recommended_structure == "RECHARGE_TRENCH"
    assert any("alluvial" in reason.casefold() for reason in result.selection_reasons)


def test_structure_rejected_when_published_footprint_does_not_fit() -> None:
    result = select_structure(
        feasibility(),
        state="NCT Delhi",
        geology="alluvial formation",
        groundwater_depth_m_bgl=10,
        building_has_basement=False,
        roof_area_m2=120,
        available_ground_area_m2=2,
    )

    assert result.status == "NO_STRUCTURE_FITS_AVAILABLE_AREA"
    assert result.recommended_structure is None
    assert "exceeds" in result.rejected_structures[-1].reason


def test_selection_does_not_generalize_delhi_table_to_other_states() -> None:
    result = select_structure(
        feasibility(),
        state="Karnataka",
        geology="alluvial formation",
        groundwater_depth_m_bgl=10,
        building_has_basement=False,
        roof_area_m2=100,
        available_ground_area_m2=10,
    )

    assert result.status == "UNSUPPORTED_LOCATION_FOR_SELECTION"
    assert result.recommended_structure is None


def test_trench_dimensions_come_from_published_roof_area_band() -> None:
    selection = select_structure(
        feasibility(),
        state="Delhi",
        geology="alluvial",
        groundwater_depth_m_bgl=10,
        building_has_basement=False,
        roof_area_m2=120,
        available_ground_area_m2=10,
    )
    result = assess_structure_size(
        selection,
        roof_area_m2=120,
        available_ground_area_m2=10,
        available_recharge_water_litres=5_000,
        post_monsoon_groundwater_depth_m=10,
    )

    assert result.status == "INDICATIVE_DESIGN_AVAILABLE"
    assert result.dimensions == {"lengthM": 1.8, "widthM": 1.5, "depthM": 1.5}
    assert result.required_footprint_m2 == 2.7
    assert len(result.filter_media) == 4


def test_trench_with_well_needs_verified_intake_zone() -> None:
    selection = select_structure(
        feasibility(groundwater_depth_m_bgl=20),
        state="Delhi",
        geology="hard rock",
        groundwater_depth_m_bgl=20,
        building_has_basement=True,
        roof_area_m2=100,
        available_ground_area_m2=10,
    )
    result = assess_structure_size(
        selection,
        roof_area_m2=100,
        available_ground_area_m2=10,
        available_recharge_water_litres=5_000,
        post_monsoon_groundwater_depth_m=20,
    )

    assert selection.recommended_structure == "TRENCH_WITH_RECHARGE_WELL"
    assert result.status == "INSUFFICIENT_DATA_FOR_SIZING"
    assert "verified granular or fractured intake zone" in result.missing_inputs


def test_trench_with_well_uses_source_depth_range_when_zone_is_verified() -> None:
    selection = select_structure(
        feasibility(groundwater_depth_m_bgl=20),
        state="Delhi",
        geology="hard rock",
        groundwater_depth_m_bgl=20,
        building_has_basement=False,
        roof_area_m2=100,
        available_ground_area_m2=10,
    )
    result = assess_structure_size(
        selection,
        roof_area_m2=100,
        available_ground_area_m2=10,
        available_recharge_water_litres=5_000,
        post_monsoon_groundwater_depth_m=20,
        aquifer_intake_zone_verified=True,
    )

    assert result.status == "INDICATIVE_DESIGN_AVAILABLE"
    assert result.dimensions is not None
    assert result.dimensions["rechargeWellDepthMinM"] == 17
    assert result.dimensions["rechargeWellDepthMaxM"] == 18
