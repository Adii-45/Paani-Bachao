from app.engineering.recharge.feasibility import (
    CriterionStatus,
    FeasibilityStatus,
    evaluate_feasibility,
)
from app.engineering.recharge.quantity import assess_recharge_quantity
from app.engineering.recharge.structure_selection import select_structure


def test_broad_soil_and_undated_depth_do_not_become_a_score() -> None:
    result = evaluate_feasibility(
        groundwater_depth_m_bgl=8,
        groundwater_has_observation_metadata=False,
        has_recharge_water_balance=False,
        has_infiltration_evidence=False,
        has_hydrogeology_evidence=False,
        has_water_quality_review=False,
        available_ground_area_m2=15,
    )

    assert result.status is FeasibilityStatus.INSUFFICIENT_DATA
    assert not hasattr(result, "score")
    by_name = {criterion.criterion: criterion for criterion in result.criteria}
    assert by_name["groundwater_observation"].result is CriterionStatus.INSUFFICIENT_DATA
    assert by_name["groundwater_observation"].observed_value == 8
    assert by_name["infiltration_or_permeability"].result is CriterionStatus.INSUFFICIENT_DATA
    assert "soil label" in by_name["infiltration_or_permeability"].reason


def test_recharge_quantity_requires_an_allocation_balance() -> None:
    result = assess_recharge_quantity()

    assert result.status == "INSUFFICIENT_DATA"
    assert result.potential_recharge_litres_per_year is None
    assert "water allocated to storage or direct use" in result.missing_inputs


def test_structure_is_not_selected_from_area_or_soil_alone() -> None:
    feasibility = evaluate_feasibility(
        groundwater_depth_m_bgl=20,
        groundwater_has_observation_metadata=False,
        has_recharge_water_balance=False,
        has_infiltration_evidence=False,
        has_hydrogeology_evidence=False,
        has_water_quality_review=False,
        available_ground_area_m2=100,
    )

    result = select_structure(feasibility)

    assert result.status == "INSUFFICIENT_DATA_FOR_SELECTION"
    assert result.recommended_structure is None
    assert result.alternative_structures == ()
    assert result.selection_reasons == ()
