import json
from pathlib import Path

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
from app.engineering.recharge.sizing import (
    METRES_PER_FOOT,
    SQUARE_METRES_PER_SQUARE_FOOT,
    assess_structure_size,
)
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
        regional_methodology_id="DELHI_CGWB_STANDARD",
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
        regional_methodology_id="DELHI_CGWB_STANDARD",
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
        regional_methodology_id="DELHI_CGWB_STANDARD",
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
        regional_methodology_id="DELHI_CGWB_STANDARD",
    )
    result = assess_structure_size(
        selection,
        roof_area_m2=120,
        available_ground_area_m2=10,
        available_recharge_water_litres=5_000,
        post_monsoon_groundwater_depth_m=10,
    )

    assert result.status == "INDICATIVE_DESIGN_AVAILABLE"
    assert result.dimensions == {
        "trenchLengthM": 1.8,
        "trenchWidthM": 1.5,
        "trenchDepthM": 1.5,
    }
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
        regional_methodology_id="DELHI_CGWB_STANDARD",
    )
    result = assess_structure_size(
        selection,
        roof_area_m2=100,
        available_ground_area_m2=10,
        available_recharge_water_litres=5_000,
        post_monsoon_groundwater_depth_m=20,
    )

    assert selection.recommended_structure == "TRENCH_WITH_RECHARGE_WELL"
    assert result.status == "PARTIAL_INDICATIVE_DESIGN"
    assert "verified granular or fractured intake zone" in result.missing_inputs
    assert result.dimensions["chamberDepthM"] == 0.5
    assert result.dimensions["finalWellTerminationDepthM"] is None


def test_trench_with_well_uses_source_depth_range_when_zone_is_verified() -> None:
    selection = select_structure(
        feasibility(groundwater_depth_m_bgl=20),
        state="Delhi",
        geology="hard rock",
        groundwater_depth_m_bgl=20,
        building_has_basement=False,
        roof_area_m2=100,
        available_ground_area_m2=10,
        regional_methodology_id="DELHI_CGWB_STANDARD",
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
    assert result.dimensions["indicativeWellTerminationDepthMinM"] == 17
    assert result.dimensions["indicativeWellTerminationDepthMaxM"] == 18


def test_bengaluru_recharge_well_uses_exact_published_kscst_row() -> None:
    roof_m2 = 1100 * 0.09290304
    open_m2 = 100 * 0.09290304
    selection = select_structure(
        feasibility(groundwater_depth_m_bgl=9.84),
        state="Karnataka",
        geology="Peninsular gneiss",
        groundwater_depth_m_bgl=9.84,
        building_has_basement=False,
        roof_area_m2=roof_m2,
        available_ground_area_m2=open_m2,
        regional_methodology_id="BENGALURU_NAQUIM_URBAN_CORE",
    )
    result = assess_structure_size(
        selection,
        roof_area_m2=roof_m2,
        available_ground_area_m2=open_m2,
        available_recharge_water_litres=5_000,
        post_monsoon_groundwater_depth_m=9.84,
    )

    assert result.status == "PARTIAL_INDICATIVE_DESIGN"
    assert result.dimensions["designStorageVolumeLitres"] == 2100
    assert result.dimensions["wellOptions"][0] == {
        "diameterM": 0.91,
        "publishedCalculatedDepthM": 3.35,
        "minimumDesignDepthM": 3.35,
        "footprintM2": 0.66,
    }
    assert result.dimensions["finalAquiferIntakeDepthM"] is None


def test_bengaluru_recharge_well_does_not_interpolate_unpublished_area() -> None:
    selection = select_structure(
        feasibility(groundwater_depth_m_bgl=9.84),
        state="Karnataka",
        geology="Peninsular gneiss",
        groundwater_depth_m_bgl=9.84,
        building_has_basement=False,
        roof_area_m2=100,
        available_ground_area_m2=10,
        regional_methodology_id="BENGALURU_NAQUIM_URBAN_CORE",
    )
    result = assess_structure_size(
        selection,
        roof_area_m2=100,
        available_ground_area_m2=10,
        available_recharge_water_litres=5_000,
    )

    assert result.status == "INSUFFICIENT_DATA_FOR_SIZING"
    assert result.dimensions is None
    assert "published KSCST" in result.missing_inputs[0]


def test_reviewed_kscst_subset_matches_published_rows_and_units() -> None:
    """KSCST, RWH Tank and Well Sizes, residential square-foot table.

    These are the exact reviewed source rows; keeping the expected transcription
    in the test catches accidental interpolation, extrapolation, or unit edits.
    """

    path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "data"
        / "source_backed"
        / "kscst_residential_recharge_well_table.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected_rows = [
        (600, 600, 0, 1100, 6, 3, 2),
        (1200, 1200, 0, 2200, 11, 6, 4),
        (1200, 1100, 100, 2100, 11, 6, 4),
        (2000, 2000, 0, 3700, 19, 11, 7),
        (2400, 2400, 0, 4500, 23, 13, 8),
        (3000, 3000, 0, 5600, 28, 16, 10),
        (3500, 3500, 0, 6500, 33, 19, 12),
        (4000, 4000, 0, 7400, 37, 21, 13),
    ]
    actual_rows = [
        (
            row["plotAreaSqFt"],
            row["roofAreaSqFt"],
            row["openAreaSqFt"],
            row["designVolumeLitres"],
            row["depth3FtDiameterFt"],
            row["depth4FtDiameterFt"],
            row["depth5FtDiameterFt"],
        )
        for row in payload["rows"]
    ]

    assert payload["areaUnit"] == "square feet"
    assert payload["wellDiameterUnit"] == "feet"
    assert payload["wellDepthUnit"] == "feet"
    assert payload["minimumWellDepthFt"] == 10
    assert actual_rows == expected_rows


def test_kscst_foot_and_square_foot_conversions_do_not_mix_dimensions() -> None:
    assert SQUARE_METRES_PER_SQUARE_FOOT == pytest.approx(0.09290304)
    assert METRES_PER_FOOT == pytest.approx(0.3048)
    assert 100 * SQUARE_METRES_PER_SQUARE_FOOT == pytest.approx(9.290304)
    assert 10 * METRES_PER_FOOT == pytest.approx(3.048)
