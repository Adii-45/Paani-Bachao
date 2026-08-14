import httpx

from app.domain.environment import LocationQuery
from app.domain.location import LocationResolutionStatus
from app.providers.location.geocoding import NominatimLocationResolver


def provider_results(*_args: object) -> list[dict[str, object]]:
    return [
        {
            "place_id": 123,
            "display_name": "Bengaluru, Bengaluru Urban, Karnataka, India",
            "lat": "12.9716",
            "lon": "77.5946",
            "importance": 0.72,
            "address": {
                "city": "Bengaluru",
                "state_district": "Bengaluru Urban",
                "state": "Karnataka",
                "country": "India",
                "country_code": "in",
            },
        }
    ]


def test_valid_text_location_resolves_to_normalized_coordinates() -> None:
    result = NominatimLocationResolver(transport=provider_results).resolve(
        LocationQuery(location="Bengaluru")
    )

    assert result.status is LocationResolutionStatus.RESOLVED
    assert result.location is not None
    assert result.location.latitude == 12.9716
    assert result.location.longitude == 77.5946
    assert result.location.district == "Bengaluru Urban"
    assert result.location.state == "Karnataka"
    assert result.location.provider_place_id == "123"
    assert result.location.confidence.startswith("PROVIDER_RANKED_FIRST")


def test_invalid_location_fails_cleanly() -> None:
    resolver = NominatimLocationResolver(transport=lambda *_args: [])

    result = resolver.resolve(LocationQuery(location="not a real location"))

    assert result.status is LocationResolutionStatus.NOT_RESOLVED
    assert result.location is None
    assert "LocationNotResolved" in result.message


def test_provider_failure_is_typed() -> None:
    def fail(*_args: object) -> list[dict[str, object]]:
        raise httpx.ConnectError("offline")

    result = NominatimLocationResolver(transport=fail).resolve(
        LocationQuery(location="Mysuru")
    )

    assert result.status is LocationResolutionStatus.PROVIDER_UNAVAILABLE
    assert result.location is None


def test_user_coordinates_are_retained_without_network() -> None:
    def must_not_call(*_args: object) -> list[dict[str, object]]:
        raise AssertionError("transport should not run")

    result = NominatimLocationResolver(transport=must_not_call).resolve(
        LocationQuery(
            location="My property",
            latitude=12.9716,
            longitude=77.5946,
            district="Bengaluru Urban",
            state="Karnataka",
        )
    )

    assert result.status is LocationResolutionStatus.RESOLVED
    assert result.location is not None
    assert result.location.provider == "USER_PROVIDED_COORDINATES"
