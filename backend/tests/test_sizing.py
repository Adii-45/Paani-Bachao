import pytest

from app.calculations.sizing import recommended_storage_litres
from app.rules.loader import load_rule


@pytest.mark.parametrize(
    ("potential", "expected_size"),
    [
        (0, 0),
        (100, 500),
        (8_333, 500),
        (8_334, 1_000),
        (80_000, 5_000),
        (400_000, 20_000),
        (1_000_000, 20_000),
    ],
)
def test_storage_sizing_rounds_up_and_honours_configured_cap(
    potential: float, expected_size: float
) -> None:
    size, message = recommended_storage_litres(
        potential, load_rule("rtrwh_sizing", "demo")
    )
    assert size == expected_size
    assert message is None


@pytest.mark.parametrize(
    "rules",
    [
        {},
        {"storageFractionOfAnnualPotential": 0.06},
        {"roundUpToLitres": 500},
        load_rule("rtrwh_sizing", "production"),
    ],
)
def test_missing_storage_rule_returns_explicit_unavailable_state(rules: dict) -> None:
    size, message = recommended_storage_litres(80_000, rules)
    assert size is None
    assert message == "Assessment unavailable. Engineering sizing rule not configured yet."
