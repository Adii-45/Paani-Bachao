import pytest

from app.rules.loader import load_rule


@pytest.fixture(autouse=True)
def use_demo_ruleset(monkeypatch: pytest.MonkeyPatch):
    """Keep every test deterministic and independent of the developer's environment."""
    monkeypatch.setenv("RAINASSESS_RULESET", "demo")
    load_rule.cache_clear()
    yield
    load_rule.cache_clear()


@pytest.fixture
def valid_payload() -> dict[str, object]:
    return {
        "location": "Bengaluru",
        "roofAreaM2": 120,
        "roofMaterial": "RCC",
        "soilType": "SANDY_LOAM",
        "groundwaterDepthM": 8,
        "availableGroundAreaM2": 15,
    }
