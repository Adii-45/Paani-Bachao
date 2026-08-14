from collections.abc import Callable
from typing import Any

import httpx

from ...domain.environment import LocationQuery
from ...domain.location import (
    LocationResolution,
    LocationResolutionStatus,
    NormalizedLocation,
)
from .cache import InMemoryLocationResolutionCache, LocationResolutionCache

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_USER_AGENT = "Paani-Bachao/0.3 (rainwater assessment location resolver)"

SearchTransport = Callable[[str, dict[str, str], dict[str, str], float], list[dict[str, Any]]]
DEFAULT_LOCATION_CACHE = InMemoryLocationResolutionCache()


def _normalized_query_part(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def _cache_key(endpoint: str, query: LocationQuery) -> str:
    return "|".join(
        (
            endpoint,
            _normalized_query_part(query.location),
            _normalized_query_part(query.district),
            _normalized_query_part(query.state),
        )
    )


def _search_text(query: LocationQuery) -> str:
    parts: list[str] = [" ".join(query.location.split())]
    included = _normalized_query_part(query.location)
    for hint in (query.district, query.state):
        normalized_hint = _normalized_query_part(hint)
        if hint and normalized_hint and normalized_hint not in included:
            parts.append(" ".join(hint.split()))
            included = f"{included} {normalized_hint}"
    return ", ".join(parts)


def _http_search(
    url: str,
    params: dict[str, str],
    headers: dict[str, str],
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    response = httpx.get(url, params=params, headers=headers, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Geocoder returned an unexpected response shape.")
    return payload


class NominatimLocationResolver:
    """Resolve Indian place text through a replaceable Nominatim endpoint.

    Nominatim ranks its returned matches. The first result is retained together with
    the candidate count and provider importance; the application does not invent a
    separate confidence score.
    """

    def __init__(
        self,
        *,
        endpoint: str = NOMINATIM_SEARCH_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = 8.0,
        transport: SearchTransport = _http_search,
        cache: LocationResolutionCache | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.cache = cache or DEFAULT_LOCATION_CACHE

    def resolve(self, query: LocationQuery) -> LocationResolution:
        if query.latitude is not None and query.longitude is not None:
            return LocationResolution(
                status=LocationResolutionStatus.RESOLVED,
                location=NormalizedLocation(
                    input=query.location,
                    canonicalName=query.location,
                    latitude=query.latitude,
                    longitude=query.longitude,
                    district=query.district,
                    state=query.state,
                    country="India",
                    provider="USER_PROVIDED_COORDINATES",
                    confidence="USER_PROVIDED",
                    candidateCount=1,
                ),
                message="User-provided coordinates were retained without geocoding.",
            )

        key = _cache_key(self.endpoint, query)
        cached = self.cache.get(key)
        if cached is not None:
            return cached.model_copy(
                update={"message": f"{cached.message} Result returned from geocoder cache."}
            )

        try:
            results = self.transport(
                self.endpoint,
                {
                    "q": _search_text(query),
                    "format": "jsonv2",
                    "addressdetails": "1",
                    "countrycodes": "in",
                    "limit": "5",
                    "accept-language": "en",
                },
                {"User-Agent": self.user_agent},
                self.timeout_seconds,
            )
            if not isinstance(results, list) or any(
                not isinstance(item, dict) for item in results
            ):
                raise ValueError("Geocoder returned an unexpected response shape.")
        except httpx.TimeoutException:
            return LocationResolution(
                status=LocationResolutionStatus.PROVIDER_UNAVAILABLE,
                message="Location provider unavailable: request timed out.",
            )
        except httpx.HTTPStatusError as exc:
            detail = "rate limited" if exc.response.status_code == 429 else "HTTP error"
            return LocationResolution(
                status=LocationResolutionStatus.PROVIDER_UNAVAILABLE,
                message=f"Location provider unavailable: {detail}.",
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            return LocationResolution(
                status=LocationResolutionStatus.PROVIDER_UNAVAILABLE,
                message=f"Location provider unavailable: {type(exc).__name__}.",
            )

        india_results = [
            item
            for item in results
            if (item.get("address") or {}).get("country_code", "").casefold() == "in"
        ]
        if not india_results:
            return LocationResolution(
                status=LocationResolutionStatus.NOT_RESOLVED,
                message="LocationNotResolved: no matching location in India was returned.",
            )

        if len(india_results) > 1:
            first_importance = india_results[0].get("importance")
            second_importance = india_results[1].get("importance")
            first_coordinates = (
                india_results[0].get("lat"),
                india_results[0].get("lon"),
            )
            second_coordinates = (
                india_results[1].get("lat"),
                india_results[1].get("lon"),
            )
            if (
                first_importance == second_importance
                and first_coordinates != second_coordinates
            ):
                ambiguous = LocationResolution(
                    status=LocationResolutionStatus.AMBIGUOUS,
                    message=(
                        "Location is ambiguous: the provider returned equally ranked "
                        "Indian matches with different coordinates. Add locality, district, "
                        "state or PIN information."
                    ),
                )
                self.cache.set(key, ambiguous)
                return ambiguous

        best = india_results[0]
        address = best.get("address") or {}
        district = next(
            (
                address.get(key)
                for key in ("state_district", "city_district", "district", "county")
                if address.get(key)
            ),
            None,
        )
        locality = next(
            (
                address.get(key)
                for key in (
                    "neighbourhood",
                    "suburb",
                    "quarter",
                    "village",
                    "town",
                    "city",
                    "municipality",
                )
                if address.get(key)
            ),
            None,
        )
        confidence_parts = ["PROVIDER_RANKED_FIRST"]
        if best.get("importance") is not None:
            confidence_parts.append(f"importance={best['importance']}")

        try:
            normalized = NormalizedLocation(
                input=query.location,
                canonicalName=str(best["display_name"]),
                latitude=float(best["lat"]),
                longitude=float(best["lon"]),
                locality=locality,
                district=district,
                state=address.get("state"),
                postalCode=address.get("postcode"),
                country=address.get("country") or "India",
                provider="OpenStreetMap Nominatim",
                providerPlaceId=str(best.get("place_id")) if best.get("place_id") else None,
                confidence="; ".join(confidence_parts),
                candidateCount=len(india_results),
            )
        except (KeyError, TypeError, ValueError) as exc:
            return LocationResolution(
                status=LocationResolutionStatus.PROVIDER_UNAVAILABLE,
                message=f"Location provider returned an unusable record: {type(exc).__name__}.",
            )

        resolution = LocationResolution(
            status=LocationResolutionStatus.RESOLVED,
            location=normalized,
            message=(
                "Location resolved using the provider's highest-ranked Indian result; "
                "provider rank and candidate count are retained."
            ),
        )
        self.cache.set(key, resolution)
        return resolution
