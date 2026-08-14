import json
from math import isfinite
from typing import Any


def parse_wgs84_feature_collection(source_text: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(source_text)
    except json.JSONDecodeError as exc:
        raise ValueError("The spatial export is not valid GeoJSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("The spatial export must be a GeoJSON object.")
    if payload.get("type") != "FeatureCollection":
        raise ValueError("The spatial export must be a GeoJSON FeatureCollection.")
    crs = payload.get("crs")
    if crs is not None and not isinstance(crs, dict):
        raise ValueError("The spatial export contains malformed CRS metadata.")
    crs_properties = (crs or {}).get("properties") or {}
    if not isinstance(crs_properties, dict):
        raise ValueError("The spatial export contains malformed CRS metadata.")
    crs_name = crs_properties.get("name")
    if crs_name and not any(
        marker in str(crs_name).casefold()
        for marker in ("epsg::4326", "epsg:4326", "crs84")
    ):
        raise ValueError("The spatial export must use WGS 84 coordinates.")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("The spatial export contains no feature list.")
    return features


def _validate_ring(ring: Any) -> list[list[float]]:
    if not isinstance(ring, list) or len(ring) < 4:
        raise ValueError("A polygon ring must contain at least four positions.")
    positions: list[list[float]] = []
    for position in ring:
        if (
            not isinstance(position, list)
            or len(position) < 2
            or isinstance(position[0], bool)
            or isinstance(position[1], bool)
            or not isinstance(position[0], (int, float))
            or not isinstance(position[1], (int, float))
        ):
            raise ValueError("A polygon contains an invalid coordinate position.")
        longitude = float(position[0])
        latitude = float(position[1])
        if (
            not isfinite(longitude)
            or not isfinite(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            raise ValueError("A polygon contains coordinates outside WGS 84 ranges.")
        positions.append([longitude, latitude])
    if positions[0] != positions[-1]:
        raise ValueError("A polygon ring must be closed.")
    twice_area = sum(
        start[0] * end[1] - end[0] * start[1]
        for start, end in zip(positions, positions[1:])
    )
    if abs(twice_area) <= 1e-12:
        raise ValueError("A polygon ring must enclose a non-zero area.")
    return positions


def validated_polygon_geometry(
    geometry: Any,
) -> tuple[dict[str, Any], tuple[float, ...]]:
    if not isinstance(geometry, dict) or geometry.get("type") not in {
        "Polygon",
        "MultiPolygon",
    }:
        raise ValueError("A spatial feature must have Polygon or MultiPolygon geometry.")
    coordinates = geometry.get("coordinates")
    polygons = [coordinates] if geometry["type"] == "Polygon" else coordinates
    if not isinstance(polygons, list) or not polygons:
        raise ValueError("A spatial feature contains no polygon coordinates.")

    normalized_polygons: list[list[list[list[float]]]] = []
    points: list[list[float]] = []
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError("A polygon contains no rings.")
        normalized_rings = [_validate_ring(ring) for ring in polygon]
        normalized_polygons.append(normalized_rings)
        for ring in normalized_rings:
            points.extend(ring)
    normalized_coordinates: Any = (
        normalized_polygons[0]
        if geometry["type"] == "Polygon"
        else normalized_polygons
    )
    longitudes = [position[0] for position in points]
    latitudes = [position[1] for position in points]
    return (
        {"type": geometry["type"], "coordinates": normalized_coordinates},
        (min(longitudes), min(latitudes), max(longitudes), max(latitudes)),
    )
