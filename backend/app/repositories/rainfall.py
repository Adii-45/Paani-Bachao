import gzip
import json
from pathlib import Path
from typing import Any

from ..domain.environment import RainfallRecord
from ..importers.spatial import validated_polygon_geometry


def _point_on_segment(
    x: float,
    y: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> bool:
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > 1e-10:
        return False
    return min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)


def _point_in_ring(longitude: float, latitude: float, ring: list[list[float]]) -> bool:
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        if _point_on_segment(longitude, latitude, x1, y1, x2, y2):
            return True
        if (y1 > latitude) != (y2 > latitude):
            intersection_x = (x2 - x1) * (latitude - y1) / (y2 - y1) + x1
            if longitude < intersection_x:
                inside = not inside
        previous = current
    return inside


def _point_in_polygon(
    longitude: float, latitude: float, polygon: list[list[list[float]]]
) -> bool:
    if not polygon or not _point_in_ring(longitude, latitude, polygon[0]):
        return False
    return not any(_point_in_ring(longitude, latitude, hole) for hole in polygon[1:])


def point_in_geometry(longitude: float, latitude: float, geometry: dict[str, Any]) -> bool:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Polygon" and isinstance(coordinates, list):
        return _point_in_polygon(longitude, latitude, coordinates)
    if geometry_type == "MultiPolygon" and isinstance(coordinates, list):
        return any(
            _point_in_polygon(longitude, latitude, polygon) for polygon in coordinates
        )
    return False


class NormalizedRainfallRepository:
    """Read the versioned local rainfall cache and perform spatial record lookup."""

    def __init__(self, dataset_path: Path) -> None:
        self.dataset_path = dataset_path

    def load(self) -> dict[str, Any]:
        if self.dataset_path.suffix == ".gz":
            with gzip.open(self.dataset_path, mode="rt", encoding="utf-8") as source:
                return json.load(source)
        with self.dataset_path.open(encoding="utf-8") as source:
            return json.load(source)

    def records(self, dataset: dict[str, Any]) -> list[RainfallRecord]:
        records = [
            RainfallRecord.model_validate(item) for item in dataset.get("records", [])
        ]
        for record in records:
            if record.geometry is None or record.bounding_box is None:
                raise ValueError(
                    "Rainfall cache records require polygon geometry and a bounding box."
                )
            _, calculated_box = validated_polygon_geometry(record.geometry)
            if any(
                abs(expected - actual) > 1e-8
                for expected, actual in zip(
                    record.bounding_box, calculated_box, strict=True
                )
            ):
                raise ValueError("Rainfall bounding box does not match geometry.")
        return records

    def find_at_coordinates(
        self,
        records: list[RainfallRecord],
        *,
        latitude: float,
        longitude: float,
    ) -> list[RainfallRecord]:
        matches: list[RainfallRecord] = []
        for record in records:
            if record.bounding_box is None or record.geometry is None:
                continue
            min_lon, min_lat, max_lon, max_lat = record.bounding_box
            if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
                continue
            if point_in_geometry(longitude, latitude, record.geometry):
                matches.append(record)
        return matches
