import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..domain.ar_environment import (
    EnvironmentalResolution,
    InfiltrationDataType,
    SoilInformation,
)
from ..provenance.models import DataQuality, ValueProvenance
from ..provenance.registry import source_registry
from .spatial import parse_wgs84_feature_collection, validated_polygon_geometry

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
        for feature in parse_wgs84_feature_collection(source_text):
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
            geometry, bounding_box = validated_polygon_geometry(feature.get("geometry"))

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
