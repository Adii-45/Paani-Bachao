import pytest


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
