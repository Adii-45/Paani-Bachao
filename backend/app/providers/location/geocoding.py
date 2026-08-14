from collections.abc import Callable
from typing import Any

import httpx

from ...domain.environment import LocationQuery
from ...domain.location import (
    LocationResolution,
    LocationResolutionStatus,
    NormalizedLocation,
)

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
DEFAULT_USER_AGENT = "Paani-Bachao/0.3 (rainwater assessment location resolver)"

SearchTransport = Callable[[str, dict[str, str], dict[str, str], float], list[dict[str, Any]]]


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
    ) -> None:
        self.endpoint = endpoint
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.transport = transport

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

        try:
            results = self.transport(
                self.endpoint,
                {
                    "q": query.location,
                    "format": "jsonv2",
                    "addressdetails": "1",
                    "countrycodes": "in",
                    "limit": "5",
                    "accept-language": "en",
                },
                {"User-Agent": self.user_agent},
                self.timeout_seconds,
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
        confidence_parts = ["PROVIDER_RANKED_FIRST"]
        if best.get("importance") is not None:
            confidence_parts.append(f"importance={best['importance']}")

        try:
            normalized = NormalizedLocation(
                input=query.location,
                canonicalName=str(best["display_name"]),
                latitude=float(best["lat"]),
                longitude=float(best["lon"]),
                district=district,
                state=address.get("state"),
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

        return LocationResolution(
            status=LocationResolutionStatus.RESOLVED,
            location=normalized,
            message=(
                "Location resolved using the provider's highest-ranked Indian result; "
                "provider rank and candidate count are retained."
            ),
        )
