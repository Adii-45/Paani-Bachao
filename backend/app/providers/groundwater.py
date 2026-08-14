from math import asin, cos, radians, sin, sqrt
from pathlib import Path

from ..domain.ar_environment import GroundwaterLookup, GroundwaterObservation
from ..domain.location import NormalizedLocation
from ..provenance.models import DataStatus
from ..provenance.registry import source_registry
from ..repositories.environmental import NormalizedEnvironmentalRepository

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "normalized"
    / "cgwb_groundwater_observations.json"
)


def _normalized_admin_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = "".join(
        character for character in value.casefold() if character.isalnum()
    )
    return normalized.replace("bengaluru", "bangalore")


def _distance_m(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    """Great-circle distance; 6,371,008.8 m is IUGG mean Earth radius."""

    earth_radius_m = 6_371_008.8
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_m * asin(sqrt(haversine))


class NormalizedCgwbGroundwaterProvider:
    """Return the nearest imported observation within the resolved district.

    A district match prevents a distant national station from being presented as
    local. No arbitrary maximum-distance engineering threshold is introduced;
    the actual distance is returned for the caller to judge.
    """

    def __init__(self, dataset_path: Path = DEFAULT_DATASET_PATH) -> None:
        self.repository = NormalizedEnvironmentalRepository(dataset_path)

    def lookup(self, location: NormalizedLocation) -> GroundwaterLookup:
        try:
            dataset = self.repository.load()
            records = self.repository.records(dataset, GroundwaterObservation)
        except (FileNotFoundError, OSError, ValueError):
            return GroundwaterLookup(
                status=DataStatus.PROVIDER_UNAVAILABLE,
                message="Groundwater provider cache could not be loaded.",
            )

        dataset_status = dataset.get("datasetStatus")
        if not records or dataset_status not in {"DATA_AVAILABLE", "DATA_STALE"}:
            return GroundwaterLookup(
                status=DataStatus.DATA_UNAVAILABLE,
                message="No reviewed CGWB groundwater observations are imported for this installation.",
            )

        district = _normalized_admin_name(location.district)
        state = _normalized_admin_name(location.state)
        candidates = [
            record
            for record in records
            if _normalized_admin_name(record.district) == district
            and _normalized_admin_name(record.state) == state
        ]
        if not candidates:
            return GroundwaterLookup(
                status=DataStatus.UNSUPPORTED_LOCATION,
                message=(
                    "Groundwater data are unavailable: no reviewed observation exists "
                    "in the resolved district. No regional default was applied."
                ),
                recordCount=len(records),
            )

        nearest = min(
            candidates,
            key=lambda item: _distance_m(
                location.latitude,
                location.longitude,
                item.latitude,
                item.longitude,
            ),
        )
        distance = _distance_m(
            location.latitude,
            location.longitude,
            nearest.latitude,
            nearest.longitude,
        )
        nearest = nearest.model_copy(update={"distance_from_property_m": round(distance, 1)})
        unknown_sources = set(nearest.provenance.source_ids) - set(source_registry())
        if unknown_sources:
            raise RuntimeError(
                f"Groundwater record uses unknown source IDs: {sorted(unknown_sources)}"
            )
        status = (
            DataStatus.DATA_STALE
            if dataset_status == "DATA_STALE"
            else DataStatus.DATA_AVAILABLE
        )
        return GroundwaterLookup(
            status=status,
            observation=nearest,
            recordCount=len(records),
            message=(
                "Nearest reviewed CGWB observation in the resolved district. This is "
                "not a property-level groundwater measurement."
            ),
        )
