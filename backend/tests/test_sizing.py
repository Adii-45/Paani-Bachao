import pytest

from app.domain.units import AreaSquareMeters, RunoffCoefficient, VolumeLitres
from app.engineering.recharge.sizing import assess_structure_size
from app.engineering.recharge.structure_selection import StructureSelectionResult
from app.engineering.rtrwh.storage import (
    StorageSizingStatus,
    assess_storage_size,
    simulate_storage,
)


IRICEN_WORKED_MONTHLY_RAINFALL = (
    30,
    8,
    5,
    15,
    38,
    61,
    98,
    136,
    122,
    282,
    354,
    141,
)


def test_storage_does_not_use_annual_volume_without_required_inputs() -> None:
    result = assess_storage_size()

    assert result.status.value == "INSUFFICIENT_DATA_FOR_SIZING"
    assert result.recommended_litres is None
    assert "twelve official monthly rainfall normals" in result.missing_inputs
    assert "planned monthly rainwater demand" in result.missing_inputs
    assert "IRICEN_RWH_2022" in result.source_ids


def test_iricen_published_monthly_worked_example() -> None:
    """IRICEN, Rain Water Harvesting (2022), §2.2.8.1, pp. 41-42.

    The published July-June table's maximum cumulative surplus is 72,610 L.
    """

    result = assess_storage_size(
        monthly_rainfall_mm=IRICEN_WORKED_MONTHLY_RAINFALL,
        roof_area=AreaSquareMeters(200),
        runoff_coefficient=RunoffCoefficient(0.85),
        monthly_demand=VolumeLitres(20_000),
    )

    assert result.status.value == "SIZE_AVAILABLE"
    assert result.recommended_litres == 72_610
    assert result.method_id == "IRICEN_2022_MONTHLY_CUMULATIVE_SURPLUS"
    assert result.design_period == "July-June normal year"
    assert result.periods[5].month == 12
    assert result.periods[5].cumulative_surplus_litres == 72_610


def test_zero_rainfall_does_not_create_a_tank_recommendation() -> None:
    result = assess_storage_size(
        monthly_rainfall_mm=(0,) * 12,
        roof_area=AreaSquareMeters(100),
        runoff_coefficient=RunoffCoefficient(0.7),
        monthly_demand=VolumeLitres(1_000),
    )

    assert result.status.value == "NO_HARVESTABLE_WATER"
    assert result.recommended_litres is None
    assert result.estimated_supply_litres == 0
    assert result.demand_met_percent == 0


def test_rainfall_without_positive_cumulative_surplus_has_no_recommendation() -> None:
    result = assess_storage_size(
        monthly_rainfall_mm=(10,) * 12,
        roof_area=AreaSquareMeters(10),
        runoff_coefficient=RunoffCoefficient(0.5),
        monthly_demand=VolumeLitres(1_000),
    )

    assert result.status == StorageSizingStatus.NO_POSITIVE_STORAGE_SURPLUS
    assert result.recommended_litres is None
    assert result.demand_met_percent is None


def test_high_rainfall_produces_explainable_capacity() -> None:
    result = assess_storage_size(
        monthly_rainfall_mm=(100,) * 12,
        roof_area=AreaSquareMeters(10),
        runoff_coefficient=RunoffCoefficient(1),
        monthly_demand=VolumeLitres(500),
    )

    # Each month contributes a 500 L surplus; the published cumulative method
    # reaches 6,000 L after twelve months.
    assert result.recommended_litres == 6_000
    assert result.estimated_supply_litres == 6_000
    assert result.demand_met_percent == 100


def test_simulation_reports_overflow_depletion_and_dry_period() -> None:
    # Rain falls only in July; the remaining eleven months form a dry period.
    rainfall = (0, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 0)
    result = simulate_storage(
        monthly_rainfall_mm=rainfall,
        roof_area=AreaSquareMeters(100),
        runoff_coefficient=RunoffCoefficient(1),
        monthly_demand=VolumeLitres(1_000),
        tank_capacity=VolumeLitres(2_000),
    )

    assert result.total_inflow_litres == 10_000
    assert result.total_supplied_litres == 3_000
    assert result.total_overflow_litres == 7_000
    assert result.depletion_months == (10, 11, 12, 1, 2, 3, 4, 5, 6)


def test_larger_tank_never_reduces_supply_for_same_series() -> None:
    rainfall = (0, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 0)
    inputs = {
        "monthly_rainfall_mm": rainfall,
        "roof_area": AreaSquareMeters(100),
        "runoff_coefficient": RunoffCoefficient(1),
        "monthly_demand": VolumeLitres(1_000),
    }

    small = simulate_storage(**inputs, tank_capacity=VolumeLitres(2_000))
    large = simulate_storage(**inputs, tank_capacity=VolumeLitres(8_000))

    assert large.total_supplied_litres >= small.total_supplied_litres
    assert large.total_overflow_litres <= small.total_overflow_litres


def test_zero_demand_is_rejected() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        assess_storage_size(
            monthly_rainfall_mm=(10,) * 12,
            roof_area=AreaSquareMeters(10),
            runoff_coefficient=RunoffCoefficient(0.7),
            monthly_demand=VolumeLitres(0),
        )


def test_negative_demand_is_rejected_by_volume_type() -> None:
    with pytest.raises(ValueError, match="Volume cannot be negative"):
        VolumeLitres(-1)


def test_ar_dimensions_are_not_fabricated_without_structure_and_inputs() -> None:
    selection = StructureSelectionResult(
        status="INSUFFICIENT_DATA_FOR_SELECTION",
        recommended_structure=None,
        alternative_structures=(),
        selection_reasons=(),
        rejected_structures=(),
        missing_inputs=("hydrogeology", "infiltration"),
        source_ids=("CGWB_MANUAL_AR_2007",),
    )

    result = assess_structure_size(selection)

    assert result.status == "INSUFFICIENT_DATA_FOR_SIZING"
    assert result.dimensions is None
    assert result.missing_inputs == ("hydrogeology", "infiltration")
