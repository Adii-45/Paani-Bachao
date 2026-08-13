import pytest

from app.domain.units import (
    AreaSquareMeters,
    RainfallMM,
    RunoffCoefficient,
)
from app.engineering.rtrwh.harvesting import (
    METHOD_ID,
    calculate_annual_harvest,
)


def test_cgwb_manual_worked_example() -> None:
    """CGWB Manual (2007), §7.2.7.1, document page 119.

    Published example: 1000 mm × 20 m² × 0.75 = 15,000 litres.
    The coefficient is used only to reproduce that example, not as an RCC default.
    """

    result = calculate_annual_harvest(
        RainfallMM(1_000), AreaSquareMeters(20), RunoffCoefficient(0.75)
    )

    assert result.gross_rainfall_volume.value == 20_000
    assert result.estimated_losses.value == 5_000
    assert result.harvestable_volume.value == 15_000
    assert result.method_id == METHOD_ID
    assert result.source_ids == ("CGWB_MANUAL_AR_2007",)


def test_established_mm_square_metre_litre_conversion() -> None:
    result = calculate_annual_harvest(
        RainfallMM(1), AreaSquareMeters(1), RunoffCoefficient(1)
    )

    assert result.gross_rainfall_volume.value == 1
    assert result.harvestable_volume.value == 1
    assert result.estimated_losses.value == 0


def test_decimal_inputs_are_rounded_only_at_output_boundary() -> None:
    result = calculate_annual_harvest(
        RainfallMM(1.111), AreaSquareMeters(1.111), RunoffCoefficient(0.777)
    )

    assert result.harvestable_volume.value == 0.96


@pytest.mark.parametrize("value", [-0.001, -1])
def test_negative_physical_values_are_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        RainfallMM(value)
    with pytest.raises(ValueError):
        AreaSquareMeters(value)


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_coefficient_outside_physical_range_is_rejected(value: float) -> None:
    with pytest.raises(ValueError):
        RunoffCoefficient(value)
