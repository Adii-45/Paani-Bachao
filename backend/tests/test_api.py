import asyncio

import httpx
import pytest

from app.main import app


def request(
    method: str,
    path: str,
    *,
    json: dict[str, object] | None = None,
    content: bytes | None = None,
    headers: dict[str, str] | None = None,
    raise_app_exceptions: bool = True,
) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(
            app=app, raise_app_exceptions=raise_app_exceptions
        )
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.request(
                method, path, json=json, content=content, headers=headers
            )

    return asyncio.run(send())


def post(payload: dict[str, object]) -> httpx.Response:
    return request("POST", "/api/assessment", json=payload)


def test_health_endpoint() -> None:
    response = request("GET", "/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_assessment_endpoint_returns_complete_contract(
    valid_payload: dict[str, object]
) -> None:
    response = post(valid_payload)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "inputs",
        "derived",
        "rtrwh",
        "artificialRecharge",
        "rtrwhSuitability",
        "dataCompleteness",
        "assessmentStatus",
        "ruleset",
        "isDemoData",
        "formula",
        "warnings",
    }
    assert body["inputs"] == valid_payload
    assert body["derived"] == {
        "annualRainfallMm": 970.0,
        "rainfallSource": "Demo configured dataset — not validated",
        "runoffCoefficient": 0.8,
    }
    assert body["rtrwh"] == {
        "potentialLitresPerYear": 93_120.0,
        "recommendedSizeLitres": 6_000.0,
        "sizingMessage": None,
    }
    assert body["artificialRecharge"]["potential"] == "HIGH"
    assert body["artificialRecharge"]["recommendedStructure"]["type"] == "RECHARGE_TRENCH"
    assert body["assessmentStatus"] == "PRELIMINARY"


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("roofAreaM2", 0),
        ("roofAreaM2", -0.1),
        ("roofAreaM2", "not-a-number"),
        ("groundwaterDepthM", -0.1),
        ("groundwaterDepthM", "unknown"),
        ("availableGroundAreaM2", -0.1),
        ("availableGroundAreaM2", "none"),
        ("location", ""),
        ("location", "   "),
        ("location", "---"),
        ("roofMaterial", "THATCH"),
        ("soilType", "PEAT"),
    ],
)
def test_invalid_field_values_return_validation_errors(
    valid_payload: dict[str, object],
    field: str,
    invalid_value: object,
) -> None:
    valid_payload[field] = invalid_value
    response = post(valid_payload)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert any(error["loc"][-1] == field for error in response.json()["detail"])


@pytest.mark.parametrize(
    "field",
    [
        "location",
        "roofAreaM2",
        "roofMaterial",
        "soilType",
        "groundwaterDepthM",
        "availableGroundAreaM2",
    ],
)
def test_every_required_field_is_enforced(
    valid_payload: dict[str, object], field: str
) -> None:
    valid_payload.pop(field)
    response = post(valid_payload)

    assert response.status_code == 422
    assert any(error["loc"][-1] == field for error in response.json()["detail"])


@pytest.mark.parametrize(
    ("field", "boundary"),
    [
        ("groundwaterDepthM", 0),
        ("availableGroundAreaM2", 0),
        ("roofAreaM2", 0.1),
    ],
)
def test_allowed_numeric_boundaries_are_accepted(
    valid_payload: dict[str, object],
    field: str,
    boundary: float,
) -> None:
    valid_payload[field] = boundary
    assert post(valid_payload).status_code == 200


def test_malformed_json_returns_a_clean_validation_response() -> None:
    response = request(
        "POST",
        "/api/assessment",
        content=b'{"location":',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"][0]["type"] == "json_invalid"


def test_unsupported_location_returns_an_incomplete_assessment_not_an_api_error(
    valid_payload: dict[str, object]
) -> None:
    valid_payload["location"] = "Atlantis"
    response = post(valid_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["derived"]["annualRainfallMm"] is None
    assert body["rtrwh"]["potentialLitresPerYear"] is None
    assert body["dataCompleteness"] == "INSUFFICIENT"
    assert "Rainfall data is not configured for this location." in body["warnings"]


def test_internal_service_failure_does_not_expose_a_stack_trace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_payload: object) -> None:
        raise RuntimeError("private implementation detail")

    monkeypatch.setattr("app.main.create_assessment", fail)
    response = request(
        "POST",
        "/api/assessment",
        json={
            "location": "Bengaluru",
            "roofAreaM2": 120,
            "roofMaterial": "RCC",
            "soilType": "SANDY_LOAM",
            "groundwaterDepthM": 8,
            "availableGroundAreaM2": 15,
        },
        raise_app_exceptions=False,
    )

    assert response.status_code == 500
    assert "private implementation detail" not in response.text
    assert "traceback" not in response.text.lower()
