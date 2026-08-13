from app.calculations.recharge import classify_recharge
from app.calculations.rtrwh import calculate_potential_litres
from app.calculations.sizing import recommended_storage_litres


def test_rtrwh_formula_uses_mm_m2_to_litres_identity() -> None:
    assert calculate_potential_litres(120, 900, 0.8) == 86_400


def test_storage_returns_unavailable_when_rule_missing() -> None:
    size, message = recommended_storage_litres(80_000, {})
    assert size is None
    assert "not configured" in message


def test_demo_recharge_rule_classification() -> None:
    rules = {
        "soilRatings": {"SANDY": {"score": 3, "rechargeFraction": 0.7}},
        "groundwaterDepthBands": [{"minInclusive": 0, "maxExclusive": None, "score": 2}],
        "availableAreaBands": [{"minInclusive": 0, "maxExclusive": None, "score": 1}],
        "classificationThresholds": [{"minimumScore": 6, "classification": "HIGH"}],
    }
    assert classify_recharge("SANDY", 8, 15, rules) == ("HIGH", 0.7)

