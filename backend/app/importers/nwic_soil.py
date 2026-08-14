import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
from typing import Any

from ..domain.ar_environment import (
    EnvironmentalResolution,
    InfiltrationDataType,
    SoilInformation,
)
from ..provenance.models import DataQuality, ValueProvenance
from ..provenance.registry import source_registry

NWIC_SOIL_SOURCE_ID = "NWIC_SOIL_SERVICE"


@dataclass(frozen=True)
class NWICSoilFieldMapping:
    """Operator-reviewed mapping from an official export to normalized fields."""

    record_id: str
    soil_class: str | None = None
    soil_texture: str | None = None
    permeability_class: str | None = None
    source_category: str | None = None
    source_code: str | None = None


def _optional_property(properties: Mapping[str, Any], field: str | None) -> str | None:
    if field is None:
        return None
    value = properties.get(field)
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _parse_feature_collection(source_text: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(source_text)
    except json.JSONDecodeError as exc:
        raise ValueError("The soil export is not valid GeoJSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("The soil export must be a GeoJSON object.")
    if payload.get("type") != "FeatureCollection":
        raise ValueError("The soil export must be a GeoJSON FeatureCollection.")
    crs = payload.get("crs")
    if crs is not None and not isinstance(crs, dict):
        raise ValueError("The soil export contains malformed CRS metadata.")
    crs_properties = (crs or {}).get("properties") or {}
    if not isinstance(crs_properties, dict):
        raise ValueError("The soil export contains malformed CRS metadata.")
    crs_name = crs_properties.get("name")
    if crs_name and not any(
        marker in str(crs_name).casefold()
        for marker in ("epsg::4326", "epsg:4326", "crs84")
    ):
        raise ValueError("The soil export must use WGS 84 longitude/latitude coordinates.")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("The soil export contains no feature list.")
    return features


def _validate_ring(ring: Any) -> list[list[float]]:
    if not isinstance(ring, list) or len(ring) < 4:
        raise ValueError("A soil polygon ring must contain at least four positions.")
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
            raise ValueError("A soil polygon contains an invalid coordinate position.")
        longitude = float(position[0])
        latitude = float(position[1])
        if (
            not isfinite(longitude)
            or not isfinite(latitude)
            or not -180 <= longitude <= 180
            or not -90 <= latitude <= 90
        ):
            raise ValueError("A soil polygon contains coordinates outside WGS 84 ranges.")
        positions.append([longitude, latitude])
    if positions[0] != positions[-1]:
        raise ValueError("A soil polygon ring must be closed.")
    twice_area = sum(
        start[0] * end[1] - end[0] * start[1]
        for start, end in zip(positions, positions[1:])
    )
    if abs(twice_area) <= 1e-12:
        raise ValueError("A soil polygon ring must enclose a non-zero area.")
    return positions


def _validated_geometry(geometry: Any) -> tuple[dict[str, Any], tuple[float, ...]]:
    if not isinstance(geometry, dict) or geometry.get("type") not in {
        "Polygon",
        "MultiPolygon",
    }:
        raise ValueError("A soil feature must have Polygon or MultiPolygon geometry.")
    coordinates = geometry.get("coordinates")
    polygons = [coordinates] if geometry["type"] == "Polygon" else coordinates
    if not isinstance(polygons, list) or not polygons:
        raise ValueError("A soil feature contains no polygon coordinates.")

    normalized_polygons: list[list[list[list[float]]]] = []
    points: list[list[float]] = []
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError("A soil polygon contains no rings.")
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


class NWICSoilPolygonImporter:
    """Normalize a reviewed official NWIC soil polygon GeoJSON export.

    The importer never derives infiltration rate from a mapped soil class. Source
    acquisition and the field mapping are explicit operator-review steps.
    """

    def normalize(
        self,
        source_text: str,
        *,
        imported_at: datetime,
        dataset_version: str,
        source_layer: str,
        spatial_resolution: str,
        fields: NWICSoilFieldMapping,
    ) -> dict[str, Any]:
        source = source_registry().get(NWIC_SOIL_SOURCE_ID)
        if source is None:
            raise ValueError(f"Unknown source ID: {NWIC_SOIL_SOURCE_ID}")
        if imported_at.tzinfo is None:
            raise ValueError("Soil import timestamp must include a timezone.")
        if (
            not dataset_version.strip()
            or not source_layer.strip()
            or not spatial_resolution.strip()
        ):
            raise ValueError(
                "Soil dataset version, source layer and spatial resolution are required."
            )

        records: list[SoilInformation] = []
        seen_ids: set[str] = set()
        for feature in _parse_feature_collection(source_text):
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise ValueError("The soil export contains a non-Feature item.")
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                raise ValueError("A soil feature contains no property object.")
            record_id = _optional_property(properties, fields.record_id)
            if record_id is None:
                raise ValueError(
                    f"A soil feature is missing source identifier field {fields.record_id}."
                )
            if record_id in seen_ids:
                raise ValueError(f"Duplicate soil polygon source identifier: {record_id}.")
            seen_ids.add(record_id)
            geometry, bounding_box = _validated_geometry(feature.get("geometry"))

            soil_class = _optional_property(properties, fields.soil_class)
            soil_texture = _optional_property(properties, fields.soil_texture)
            permeability = _optional_property(properties, fields.permeability_class)
            category = _optional_property(properties, fields.source_category)
            code = _optional_property(properties, fields.source_code)
            source_attributes = "; ".join(
                f"{label}={value}"
                for label, value in (
                    (fields.soil_class, soil_class),
                    (fields.soil_texture, soil_texture),
                    (fields.permeability_class, permeability),
                    (fields.source_category, category),
                    (fields.source_code, code),
                )
                if label is not None and value is not None
            )
            records.append(
                SoilInformation(
                    recordId=f"nwic-soil-{record_id}",
                    soilClass=soil_class,
                    soilTexture=soil_texture,
                    permeabilityClass=permeability,
                    sourceCategory=category,
                    sourceCode=code,
                    datasetName=source.document_title,
                    datasetVersion=dataset_version,
                    sourceOrganization=source.authority,
                    measuredInfiltrationRateMmPerHr=None,
                    infiltrationDataType=InfiltrationDataType.REGIONAL_SOIL_PROXY,
                    spatialResolution=EnvironmentalResolution.REGIONAL_LAYER,
                    fieldTestRecommended=True,
                    boundingBox=bounding_box,
                    geometry=geometry,
                    provenance=ValueProvenance(
                        quality=DataQuality.AUTHORITATIVE_DATASET,
                        sourceIds=[NWIC_SOIL_SOURCE_ID],
                        sourceRecord=(
                            f"Layer {source_layer}; feature {record_id}"
                            + (f"; {source_attributes}" if source_attributes else "")
                        ),
                        sourceDateOrVersion=dataset_version,
                        spatialResolution=spatial_resolution,
                        retrievedAt=imported_at.astimezone(UTC),
                        notes=(
                            "Regional mapped classification only. No property-level "
                            "infiltration rate is derived; field testing is recommended."
                        ),
                    ),
                )
            )

        if not records:
            raise ValueError("The soil export contains no polygon records.")
        records.sort(key=lambda record: record.record_id)
        return {
            "datasetStatus": "DATA_AVAILABLE",
            "datasetVersion": dataset_version,
            "datasetName": source.document_title,
            "sourceOrganization": source.authority,
            "sourceId": NWIC_SOIL_SOURCE_ID,
            "sourceUrl": source.source_url,
            "sourceLayer": source_layer,
            "spatialResolution": spatial_resolution,
            "importedAt": imported_at.astimezone(UTC).isoformat(),
            "sourceSha256": hashlib.sha256(source_text.encode()).hexdigest(),
            "recordCount": len(records),
            "records": [
                record.model_dump(mode="json", by_alias=True) for record in records
            ],
        }

    @staticmethod
    def write(normalized: dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
