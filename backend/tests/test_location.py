import httpx
import pytest
from pydantic import ValidationError

from app.domain.environment import LocationQuery
from app.domain.location import LocationResolutionStatus
from app.providers.location.cache import InMemoryLocationResolutionCache
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
                "suburb": "Indiranagar",
                "postcode": "560038",
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
    assert result.location.locality == "Indiranagar"
    assert result.location.postal_code == "560038"
    assert result.location.provider_place_id == "123"
    assert result.location.confidence.startswith("PROVIDER_RANKED_FIRST")


def test_invalid_location_fails_cleanly() -> None:
    resolver = NominatimLocationResolver(transport=lambda *_args: [])

    result = resolver.resolve(LocationQuery(location="not a real location"))

    assert result.status is LocationResolutionStatus.NOT_RESOLVED
    assert result.location is None
    assert "LocationNotResolved" in result.message


def test_zero_results_are_not_cached_as_a_long_lived_false_negative() -> None:
    call_count = 0

    def no_results(*_args: object) -> list[dict[str, object]]:
        nonlocal call_count
        call_count += 1
        return []

    resolver = NominatimLocationResolver(
        transport=no_results,
        cache=InMemoryLocationResolutionCache(),
    )

    first = resolver.resolve(LocationQuery(location="Unknown locality"))
    second = resolver.resolve(LocationQuery(location="Unknown locality"))

    assert first.status is LocationResolutionStatus.NOT_RESOLVED
    assert second.status is LocationResolutionStatus.NOT_RESOLVED
    assert call_count == 2


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


def test_pin_code_query_resolves_and_preserves_postal_code() -> None:
    captured_query: dict[str, str] = {}

    def pin_results(
        _url: str,
        params: dict[str, str],
        _headers: dict[str, str],
        _timeout: float,
    ) -> list[dict[str, object]]:
        captured_query.update(params)
        return provider_results()

    result = NominatimLocationResolver(
        transport=pin_results,
        cache=InMemoryLocationResolutionCache(),
    ).resolve(LocationQuery(location="560038"))

    assert result.status is LocationResolutionStatus.RESOLVED
    assert result.location is not None
    assert result.location.postal_code == "560038"
    assert captured_query["q"] == "560038"
    assert captured_query["countrycodes"] == "in"


def test_district_and_state_hints_are_sent_to_geocoder() -> None:
    captured_query: dict[str, str] = {}

    def capture(
        _url: str,
        params: dict[str, str],
        _headers: dict[str, str],
        _timeout: float,
    ) -> list[dict[str, object]]:
        captured_query.update(params)
        return provider_results()

    result = NominatimLocationResolver(
        transport=capture,
        cache=InMemoryLocationResolutionCache(),
    ).resolve(
        LocationQuery(
            location="Indiranagar",
            district="Bengaluru Urban",
            state="Karnataka",
        )
    )

    assert result.status is LocationResolutionStatus.RESOLVED
    assert captured_query["q"] == "Indiranagar, Bengaluru Urban, Karnataka"


def test_equal_ranked_different_coordinates_are_ambiguous() -> None:
    second = {
        **provider_results()[0],
        "place_id": 456,
        "display_name": "Another Bengaluru, Karnataka, India",
        "lat": "13.1000",
        "lon": "77.7000",
    }
    resolver = NominatimLocationResolver(
        transport=lambda *_args: [provider_results()[0], second],
        cache=InMemoryLocationResolutionCache(),
    )

    result = resolver.resolve(LocationQuery(location="Bengaluru"))

    assert result.status is LocationResolutionStatus.AMBIGUOUS
    assert result.location is None
    assert "equally ranked" in result.message


def test_provider_timeout_is_typed_and_not_cached() -> None:
    call_count = 0

    def timeout(*_args: object) -> list[dict[str, object]]:
        nonlocal call_count
        call_count += 1
        raise httpx.ReadTimeout("slow provider")

    resolver = NominatimLocationResolver(
        transport=timeout,
        cache=InMemoryLocationResolutionCache(),
    )

    first = resolver.resolve(LocationQuery(location="Mysuru"))
    second = resolver.resolve(LocationQuery(location="Mysuru"))

    assert first.status is LocationResolutionStatus.PROVIDER_UNAVAILABLE
    assert second.status is LocationResolutionStatus.PROVIDER_UNAVAILABLE
    assert call_count == 2


def test_rate_limit_is_typed_and_not_cached() -> None:
    call_count = 0
    request = httpx.Request("GET", "https://example.invalid/search")
    response = httpx.Response(429, request=request)

    def rate_limited(*_args: object) -> list[dict[str, object]]:
        nonlocal call_count
        call_count += 1
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    resolver = NominatimLocationResolver(
        transport=rate_limited,
        cache=InMemoryLocationResolutionCache(),
    )

    first = resolver.resolve(LocationQuery(location="Mysuru"))
    second = resolver.resolve(LocationQuery(location="Mysuru"))

    assert first.status is LocationResolutionStatus.PROVIDER_UNAVAILABLE
    assert "rate limited" in first.message
    assert second.status is LocationResolutionStatus.PROVIDER_UNAVAILABLE
    assert call_count == 2


def test_malformed_provider_response_fails_cleanly() -> None:
    resolver = NominatimLocationResolver(
        transport=lambda *_args: ["not-an-object"],  # type: ignore[list-item]
        cache=InMemoryLocationResolutionCache(),
    )

    result = resolver.resolve(LocationQuery(location="Mysuru"))

    assert result.status is LocationResolutionStatus.PROVIDER_UNAVAILABLE
    assert result.location is None


@pytest.mark.parametrize(("field", "value"), (("lat", "91"), ("lon", "181")))
def test_provider_coordinate_outside_valid_range_is_rejected(
    field: str, value: str
) -> None:
    invalid = {**provider_results()[0], field: value}
    resolver = NominatimLocationResolver(
        transport=lambda *_args: [invalid],
        cache=InMemoryLocationResolutionCache(),
    )

    result = resolver.resolve(LocationQuery(location="Invalid provider coordinate"))

    assert result.status is LocationResolutionStatus.PROVIDER_UNAVAILABLE
    assert result.location is None


def test_successful_resolution_uses_normalized_query_cache() -> None:
    call_count = 0
    cache = InMemoryLocationResolutionCache()

    def counted(*_args: object) -> list[dict[str, object]]:
        nonlocal call_count
        call_count += 1
        return provider_results()

    resolver = NominatimLocationResolver(transport=counted, cache=cache)

    first = resolver.resolve(LocationQuery(location="  Indiranagar,   Bengaluru "))
    second = resolver.resolve(LocationQuery(location="indiranagar, bengaluru"))

    assert first.status is LocationResolutionStatus.RESOLVED
    assert second.status is LocationResolutionStatus.RESOLVED
    assert call_count == 1
    assert "cache" in second.message.casefold()


def test_different_queries_are_cache_misses() -> None:
    call_count = 0

    def counted(*_args: object) -> list[dict[str, object]]:
        nonlocal call_count
        call_count += 1
        return provider_results()

    resolver = NominatimLocationResolver(
        transport=counted,
        cache=InMemoryLocationResolutionCache(),
    )
    resolver.resolve(LocationQuery(location="Bengaluru"))
    resolver.resolve(LocationQuery(location="Mysuru"))

    assert call_count == 2


@pytest.mark.parametrize(
    ("field", "value"),
    (("latitude", 90.1), ("latitude", -90.1), ("longitude", 180.1), ("longitude", -180.1)),
)
def test_invalid_coordinate_is_rejected(field: str, value: float) -> None:
    coordinates = {"latitude": 12.0, "longitude": 77.0, field: value}

    with pytest.raises(ValidationError):
        LocationQuery(location="Property", **coordinates)


def test_partial_coordinate_pair_is_rejected() -> None:
    with pytest.raises(ValidationError, match="supplied together"):
        LocationQuery(location="Property", latitude=12.0)
