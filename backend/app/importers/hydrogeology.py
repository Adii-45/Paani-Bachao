import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..domain.ar_environment import (
    EnvironmentalResolution,
    HydrogeologyFeatureType,
    HydrogeologyInformation,
)
from ..provenance.models import DataQuality, ValueProvenance
from ..provenance.registry import source_registry
from .spatial import parse_wgs84_feature_collection, validated_polygon_geometry

APPROVED_HYDROGEOLOGY_SOURCE_IDS = {"NWIC_GSI_AQUIFER_SYSTEMS"}
APPROVED_SOURCE_FEATURE_TYPES = {
    "NWIC_GSI_AQUIFER_SYSTEMS": {
        HydrogeologyFeatureType.GEOLOGY,
        HydrogeologyFeatureType.AQUIFER,
    }
}


@dataclass(frozen=True)
class HydrogeologyFieldMapping:
    record_id: str
    geology: str | None = None
    lithology: str | None = None
    geomorphology: str | None = None
    groundwater_prospect: str | None = None
    aquifer_type: str | None = None
    aquifer_depth: str | None = None
    aquifer_thickness: str | None = None
    aquifer_characteristics: Mapping[str, str] = field(default_factory=dict)


def _optional_property(properties: Mapping[str, Any], field_name: str | None) -> str | None:
    if field_name is None:
        return None
    value = properties.get(field_name)
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def _validate_semantic_mapping(
    feature_type: HydrogeologyFeatureType, fields: HydrogeologyFieldMapping
) -> None:
    supplied = {
        "geology": fields.geology,
        "lithology": fields.lithology,
        "geomorphology": fields.geomorphology,
        "groundwater_prospect": fields.groundwater_prospect,
        "aquifer_type": fields.aquifer_type,
        "aquifer_depth": fields.aquifer_depth,
        "aquifer_thickness": fields.aquifer_thickness,
        "aquifer_characteristics": (
            "mapped" if fields.aquifer_characteristics else None
        ),
    }
    allowed = {
        HydrogeologyFeatureType.GEOLOGY: {"geology", "lithology"},
        HydrogeologyFeatureType.GEOMORPHOLOGY: {"geomorphology"},
        HydrogeologyFeatureType.AQUIFER: {
            "aquifer_type",
            "aquifer_depth",
            "aquifer_thickness",
            "aquifer_characteristics",
        },
        HydrogeologyFeatureType.GROUNDWATER_PROSPECT: {"groundwater_prospect"},
    }
    permitted = allowed.get(feature_type)
    if permitted is None:
        raise ValueError("COMBINED is a response type and cannot be imported.")
    invalid = sorted(
        name for name, value in supplied.items() if value and name not in permitted
    )
    if invalid:
        raise ValueError(
            f"Field mapping is incompatible with {feature_type.value}: "
            f"{', '.join(invalid)}."
        )


class OfficialHydrogeologyPolygonImporter:
    """Normalize one reviewed official hydrogeology polygon layer at a time."""

    def normalize(
        self,
        source_text: str,
        *,
        source_id: str,
        feature_type: HydrogeologyFeatureType,
        imported_at: datetime,
        dataset_version: str,
        source_layer: str,
        spatial_resolution: str,
        fields: HydrogeologyFieldMapping,
    ) -> dict[str, Any]:
        if source_id not in APPROVED_HYDROGEOLOGY_SOURCE_IDS:
            raise ValueError(f"Hydrogeology source is not approved: {source_id}.")
        if feature_type not in APPROVED_SOURCE_FEATURE_TYPES[source_id]:
            raise ValueError(
                f"{source_id} is not approved for {feature_type.value} attributes."
            )
        source = source_registry().get(source_id)
        if source is None:
            raise ValueError(f"Unknown source ID: {source_id}.")
        if imported_at.tzinfo is None:
            raise ValueError("Hydrogeology import timestamp must include a timezone.")
        if (
            not dataset_version.strip()
            or not source_layer.strip()
            or not spatial_resolution.strip()
        ):
            raise ValueError(
                "Dataset version, source layer and spatial resolution are required."
            )
        _validate_semantic_mapping(feature_type, fields)

        records: list[HydrogeologyInformation] = []
        seen_ids: set[str] = set()
        for feature in parse_wgs84_feature_collection(source_text):
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise ValueError("The hydrogeology export contains a non-Feature item.")
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                raise ValueError("A hydrogeology feature contains no property object.")
            source_feature_id = _optional_property(properties, fields.record_id)
            if source_feature_id is None:
                raise ValueError(
                    "A hydrogeology feature is missing its mapped source identifier."
                )
            if source_feature_id in seen_ids:
                raise ValueError(
                    f"Duplicate hydrogeology source identifier: {source_feature_id}."
                )
            seen_ids.add(source_feature_id)
            geometry, bounding_box = validated_polygon_geometry(feature.get("geometry"))

            characteristics = {
                normalized_name: value
                for normalized_name, source_field in sorted(
                    fields.aquifer_characteristics.items()
                )
                if (value := _optional_property(properties, source_field)) is not None
            }
            records.append(
                HydrogeologyInformation(
                    recordId=(
                        f"{source_id.casefold()}-{feature_type.value.casefold()}-"
                        f"{source_feature_id}"
                    ),
                    featureType=feature_type,
                    sourceFeatureId=source_feature_id,
                    geology=_optional_property(properties, fields.geology),
                    lithology=_optional_property(properties, fields.lithology),
                    geomorphology=_optional_property(properties, fields.geomorphology),
                    groundwaterProspect=_optional_property(
                        properties, fields.groundwater_prospect
                    ),
                    aquiferType=_optional_property(properties, fields.aquifer_type),
                    aquiferDepth=_optional_property(properties, fields.aquifer_depth),
                    aquiferThickness=_optional_property(
                        properties, fields.aquifer_thickness
                    ),
                    aquiferCharacteristics=characteristics,
                    spatialResolution=EnvironmentalResolution.REGIONAL_LAYER,
                    datasetVersion=dataset_version,
                    datasetName=source.document_title,
                    sourceLayer=source_layer,
                    sourceOrganization=source.authority,
                    boundingBox=bounding_box,
                    geometry=geometry,
                    provenance=ValueProvenance(
                        quality=DataQuality.AUTHORITATIVE_DATASET,
                        sourceIds=[source_id],
                        sourceRecord=(
                            f"Layer {source_layer}; feature {source_feature_id}; "
                            f"type={feature_type.value}"
                        ),
                        sourceDateOrVersion=dataset_version,
                        spatialResolution=spatial_resolution,
                        retrievedAt=imported_at.astimezone(UTC),
                        notes=(
                            "Mapped regional source attributes only. Missing properties "
                            "remain null and no recharge score is derived."
                        ),
                    ),
                )
            )

        if not records:
            raise ValueError("The hydrogeology export contains no polygon records.")
        records.sort(key=lambda record: record.record_id)
        return {
            "datasetStatus": "DATA_AVAILABLE",
            "datasetVersion": dataset_version,
            "datasetName": source.document_title,
            "sourceOrganization": source.authority,
            "sourceId": source_id,
            "sourceUrl": source.source_url,
            "sourceLayer": source_layer,
            "featureType": feature_type.value,
            "spatialResolution": spatial_resolution,
            "importedAt": imported_at.astimezone(UTC).isoformat(),
            "sourceSha256": hashlib.sha256(source_text.encode()).hexdigest(),
            "recordCount": len(records),
            "records": [
                record.model_dump(mode="json", by_alias=True) for record in records
            ],
        }

    @staticmethod
    def combine(
        datasets: list[dict[str, Any]], *, imported_at: datetime
    ) -> dict[str, Any]:
        if imported_at.tzinfo is None:
            raise ValueError("Combined-cache timestamp must include a timezone.")
        records: list[HydrogeologyInformation] = []
        seen_ids: set[str] = set()
        registry = source_registry()
        for dataset in datasets:
            if dataset.get("datasetStatus") != "DATA_AVAILABLE":
                raise ValueError("Only available reviewed datasets can be combined.")
            for item in dataset.get("records", []):
                record = HydrogeologyInformation.model_validate(item)
                unknown_sources = set(record.provenance.source_ids) - set(registry)
                if unknown_sources:
                    raise ValueError(
                        f"Unknown hydrogeology source IDs: {sorted(unknown_sources)}."
                    )
                if record.feature_type is HydrogeologyFeatureType.COMBINED:
                    raise ValueError("A composed response cannot be imported into a cache.")
                if record.record_id in seen_ids:
                    raise ValueError(
                        f"Duplicate normalized hydrogeology record: {record.record_id}."
                    )
                seen_ids.add(record.record_id)
                records.append(record)
        if not records:
            raise ValueError("No hydrogeology records were supplied for combination.")
        records.sort(key=lambda record: record.record_id)
        return {
            "datasetStatus": "DATA_AVAILABLE",
            "datasetVersion": "combined reviewed hydrogeology layers",
            "importedAt": imported_at.astimezone(UTC).isoformat(),
            "recordCount": len(records),
            "sourceIds": sorted(
                {
                    source_id
                    for record in records
                    for source_id in record.provenance.source_ids
                }
            ),
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
