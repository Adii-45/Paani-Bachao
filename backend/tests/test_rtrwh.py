import pytest

from app.calculations.rtrwh import calculate_potential_litres


@pytest.mark.parametrize(
    ("roof_area_m2", "rainfall_mm", "coefficient", "expected_litres"),
    [
        (25, 800, 0.8, 16_000),
        (100, 1_000, 0.8, 80_000),
        (350, 2_200, 0.85, 654_500),
        (42.5, 970, 0.75, 30_918.75),
        (12.25, 850.5, 0.8, 8_334.9),
        (0, 970, 0.8, 0),
    ],
)
def test_potential_uses_mm_m2_to_litres_identity(
    roof_area_m2: float,
    rainfall_mm: float,
    coefficient: float,
    expected_litres: float,
) -> None:
    assert (
        calculate_potential_litres(roof_area_m2, rainfall_mm, coefficient)
        == expected_litres
    )


def test_potential_is_rounded_to_two_decimal_places() -> None:
    assert calculate_potential_litres(1.111, 1.111, 0.777) == 0.96
