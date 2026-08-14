import asyncio

import httpx
import pytest

from app.domain.location import LocationResolution, LocationResolutionStatus
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


def test_assessment_endpoint_returns_evidence_aware_contract(
    valid_payload: dict[str, object]
) -> None:
    response = post(valid_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["inputs"]["location"] == valid_payload["location"]
    assert body["derived"]["locationStatus"] == "RESOLVED"
    assert body["derived"]["normalizedLocation"]["latitude"] == 12.9716
    assert body["derived"]["rainfallStatus"] == "DATA_AVAILABLE"
    assert body["derived"]["rainfall"]["value"] == 822.1
    assert body["derived"]["rainfall"]["referencePeriod"] == "1971-2020"
    assert body["rtrwh"]["calculationStatus"] == "DATA_AVAILABLE"
    assert body["rtrwh"]["potentialLitresPerYear"] == 69_056.4
    assert body["rtrwh"]["sizingStatus"] == "INSUFFICIENT_DATA_FOR_SIZING"
    assert body["artificialRecharge"]["feasibilityStatus"] == "INSUFFICIENT_DATA"
    assert body["artificialRecharge"]["structureSelectionStatus"] == (
        "INSUFFICIENT_DATA_FOR_SELECTION"
    )
    assert body["ruleset"] == "SOURCE_BACKED"
    assert body["isDemoData"] is False
    assert body["sources"]


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
        ("latitude", 91),
        ("longitude", -181),
        ("monthlyRainwaterDemandLitres", 0),
        ("monthlyRainwaterDemandLitres", -1),
    ],
)
def test_invalid_field_values_return_validation_errors(
    valid_payload: dict[str, object], field: str, invalid_value: object
) -> None:
    valid_payload[field] = invalid_value
    response = post(valid_payload)

    assert response.status_code == 422
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
def test_every_existing_required_field_is_enforced(
    valid_payload: dict[str, object], field: str
) -> None:
    valid_payload.pop(field)
    response = post(valid_payload)

    assert response.status_code == 422
    assert any(error["loc"][-1] == field for error in response.json()["detail"])


def test_malformed_json_returns_clean_validation_response() -> None:
    response = request(
        "POST",
        "/api/assessment",
        content=b'{"location":',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")


def test_assessment_endpoint_sizes_storage_when_monthly_demand_is_supplied(
    valid_payload: dict[str, object]
) -> None:
    valid_payload["roofAreaM2"] = 20
    valid_payload["monthlyRainwaterDemandLitres"] = 500

    response = post(valid_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["rtrwh"]["sizingStatus"] == "SIZE_AVAILABLE"
    assert body["rtrwh"]["recommendedSizeLitres"] == 5_538.8
    assert body["rtrwh"]["sizingRainfallReferencePeriod"] == "1971-2020"
    assert body["rtrwh"]["demandUsedLitresPerMonth"] == 500
    assert len(body["rtrwh"]["storagePeriods"]) == 12


def test_location_resolution_failure_returns_typed_unavailable_result(
    valid_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    valid_payload.pop("latitude")
    valid_payload.pop("longitude")
    monkeypatch.setattr(
        "app.services.assessment.NominatimLocationResolver.resolve",
        lambda _self, _query: LocationResolution(
            status=LocationResolutionStatus.NOT_RESOLVED,
            message="LocationNotResolved: fixture.",
        ),
    )

    response = post(valid_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["derived"]["locationStatus"] == "NOT_RESOLVED"
    assert body["derived"]["normalizedLocation"] is None
    assert body["derived"]["rainfall"]["errorCode"] == "LOCATION_NOT_RESOLVED"
    assert body["rtrwh"]["potentialLitresPerYear"] is None


def test_internal_service_failure_does_not_expose_stack_trace(
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
