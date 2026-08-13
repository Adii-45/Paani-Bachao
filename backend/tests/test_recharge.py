import pytest

from app.calculations.recharge import classify_recharge, select_structure
from app.rules.loader import load_rule


@pytest.mark.parametrize(
    ("soil", "depth", "area", "classification", "fraction"),
    [
        ("SANDY", 8, 10, "HIGH", 0.75),
        ("LOAM", 8, 4, "MEDIUM", 0.5),
        ("CLAYEY", 3, 4, "LOW", 0.25),
        ("ROCKY", 0, 0, "NOT_RECOMMENDED", 0.1),
    ],
)
def test_each_configured_recharge_classification(
    soil: str,
    depth: float,
    area: float,
    classification: str,
    fraction: float,
) -> None:
    rules = load_rule("recharge_rules", "demo")
    assert classify_recharge(soil, depth, area, rules) == (classification, fraction)


@pytest.mark.parametrize(
    ("depth", "area", "expected"),
    [
        (2.999, 3.999, "LOW"),
        (3, 4, "MEDIUM"),
        (7.999, 9.999, "MEDIUM"),
        (8, 10, "HIGH"),
        (19.999, 10, "HIGH"),
        (20, 10, "HIGH"),
    ],
)
def test_depth_and_area_band_boundaries(
    depth: float, area: float, expected: str
) -> None:
    rules = load_rule("recharge_rules", "demo")
    classification, _ = classify_recharge("SANDY", depth, area, rules)
    assert classification == expected


@pytest.mark.parametrize("soil", ["DONT_KNOW", "PEAT", "", "sandy"])
def test_unknown_or_unsupported_soil_is_unavailable(soil: str) -> None:
    assert classify_recharge(
        soil, 8, 15, load_rule("recharge_rules", "demo")
    ) == (None, None)


@pytest.mark.parametrize(
    "rules",
    [
        {},
        {"soilRatings": {"SANDY": {"score": 3}}},
        load_rule("recharge_rules", "production"),
    ],
)
def test_missing_recharge_rules_are_unavailable(rules: dict) -> None:
    assert classify_recharge("SANDY", 8, 15, rules) == (None, None)


@pytest.mark.parametrize(
    ("classification", "area", "expected_type", "expected_dimensions"),
    [
        ("HIGH", 9, "RECHARGE_TRENCH", {"lengthM": 3, "widthM": 1, "depthM": 1.5}),
        ("MEDIUM", 9, "RECHARGE_TRENCH", {"lengthM": 3, "widthM": 1, "depthM": 1.5}),
        ("HIGH", 4, "RECHARGE_PIT", {"lengthM": 2, "widthM": 2, "depthM": 2}),
        ("LOW", 9, "RECHARGE_PIT", {"lengthM": 2, "widthM": 2, "depthM": 2}),
    ],
)
def test_structure_selection_and_configured_dimensions(
    classification: str,
    area: float,
    expected_type: str,
    expected_dimensions: dict[str, float],
) -> None:
    structure, dimensions = select_structure(
        classification, area, load_rule("ar_structures", "demo")
    )

    assert structure is not None
    assert structure["type"] == expected_type
    assert dimensions == expected_dimensions


@pytest.mark.parametrize(
    ("classification", "area", "rules"),
    [
        ("HIGH", 3.999, load_rule("ar_structures", "demo")),
        ("NOT_RECOMMENDED", 20, load_rule("ar_structures", "demo")),
        (None, 20, load_rule("ar_structures", "demo")),
        ("HIGH", 20, load_rule("ar_structures", "production")),
    ],
)
def test_structure_is_unavailable_when_no_rule_matches(
    classification: str | None, area: float, rules: dict
) -> None:
    assert select_structure(classification, area, rules) == (None, None)
