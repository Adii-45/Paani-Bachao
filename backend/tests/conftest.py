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
        "latitude": 12.9716,
        "longitude": 77.5946,
        "state": "Karnataka",
        "district": "Bengaluru Urban",
    }
