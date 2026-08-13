import pytest

from app.rules.loader import load_rule
from app.services.rainfall import get_rainfall, normalize_location


@pytest.mark.parametrize(
    ("location", "expected_name", "expected_rainfall"),
    [
        ("Bengaluru", "Bengaluru", 970),
        ("  BANGALORE  ", "Bengaluru", 970),
        ("560001", "Bengaluru", 970),
        ("New, Delhi", "Delhi", 800),
        ("400001", "Mumbai", 2_200),
    ],
)
def test_configured_location_and_alias_lookup(
    location: str, expected_name: str, expected_rainfall: float
) -> None:
    result = get_rainfall(location, load_rule("rainfall", "demo"))

    assert result is not None
    assert result["name"] == expected_name
    assert result["annualRainfallMm"] == expected_rainfall
    assert "not validated" in result["source"].lower()


@pytest.mark.parametrize("location", ["Atlantis", "", "   ", "---", "5600O1"])
def test_unconfigured_or_malformed_location_has_no_fabricated_default(
    location: str,
) -> None:
    assert get_rainfall(location, load_rule("rainfall", "demo")) is None


def test_lookup_uses_a_configured_default_only_when_present() -> None:
    default = {"annualRainfallMm": 500, "source": "test fixture"}
    config = {"locations": [], "default": default}

    assert get_rainfall("unlisted", config) is default


def test_location_normalization_is_case_and_punctuation_tolerant() -> None:
    assert normalize_location("  New,   DELHI ") == "new delhi"


def test_production_rainfall_placeholder_is_unavailable() -> None:
    assert get_rainfall("Bengaluru", load_rule("rainfall", "production")) is None
