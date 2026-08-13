import asyncio

import httpx
import pytest

from app.main import app


def post(payload: dict) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/api/assessment", json=payload)

    return asyncio.run(request())


def valid_payload() -> dict:
    return {
        "location": "Bengaluru",
        "roofAreaM2": 120,
        "roofMaterial": "RCC",
        "soilType": "SANDY_LOAM",
        "groundwaterDepthM": 8,
        "availableGroundAreaM2": 15,
    }


def test_assessment_end_to_end() -> None:
    response = post(valid_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["rtrwh"]["potentialLitresPerYear"] == 93_120
    assert body["assessmentStatus"] == "PRELIMINARY"
    assert body["isDemoData"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("roofAreaM2", 0),
        ("roofAreaM2", -1),
        ("groundwaterDepthM", -1),
        ("availableGroundAreaM2", -1),
        ("location", ""),
        ("roofMaterial", "THATCH"),
        ("soilType", "PEAT"),
    ],
)
def test_invalid_inputs_are_rejected(field: str, value: object) -> None:
    payload = valid_payload()
    payload[field] = value
    response = post(payload)
    assert response.status_code == 422


def test_unknown_material_returns_incomplete_not_fabricated_result() -> None:
    payload = valid_payload()
    payload["roofMaterial"] = "DONT_KNOW"
    response = post(payload)
    assert response.status_code == 200
    assert response.json()["rtrwh"]["potentialLitresPerYear"] is None
    assert response.json()["dataCompleteness"] == "INSUFFICIENT"
