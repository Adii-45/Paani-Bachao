"""Normalize one reviewed official hydrogeology polygon GeoJSON layer."""

import argparse
from datetime import UTC, datetime
from pathlib import Path

from app.domain.ar_environment import HydrogeologyFeatureType
from app.importers.hydrogeology import (
    APPROVED_HYDROGEOLOGY_SOURCE_IDS,
    APPROVED_SOURCE_FEATURE_TYPES,
    HydrogeologyFieldMapping,
    OfficialHydrogeologyPolygonImporter,
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "data"
    / "normalized"
    / "official_hydrogeology_information.json"
)


def _characteristic(value: str) -> tuple[str, str]:
    normalized_name, separator, source_field = value.partition("=")
    if not separator or not normalized_name.strip() or not source_field.strip():
        raise argparse.ArgumentTypeError(
            "Aquifer characteristics must use NORMALIZED_NAME=SOURCE_FIELD."
        )
    return normalized_name.strip(), source_field.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument(
        "--source-id", required=True, choices=sorted(APPROVED_HYDROGEOLOGY_SOURCE_IDS)
    )
    parser.add_argument(
        "--feature-type",
        required=True,
        choices=[
            item.value
            for item in sorted(
                set().union(*APPROVED_SOURCE_FEATURE_TYPES.values()),
                key=lambda item: item.value,
            )
        ],
    )
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--source-layer", required=True)
    parser.add_argument("--spatial-resolution", required=True)
    parser.add_argument("--record-id-field", required=True)
    parser.add_argument("--geology-field")
    parser.add_argument("--lithology-field")
    parser.add_argument("--geomorphology-field")
    parser.add_argument("--groundwater-prospect-field")
    parser.add_argument("--aquifer-type-field")
    parser.add_argument("--aquifer-depth-field")
    parser.add_argument("--aquifer-thickness-field")
    parser.add_argument(
        "--aquifer-characteristic", action="append", default=[], type=_characteristic
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--confirm-official-source", action="store_true")
    args = parser.parse_args()
    if not args.confirm_official_source:
        parser.error("--confirm-official-source is required")

    normalized = OfficialHydrogeologyPolygonImporter().normalize(
        args.source.read_text(encoding="utf-8-sig"),
        source_id=args.source_id,
        feature_type=HydrogeologyFeatureType(args.feature_type),
        imported_at=datetime.now(UTC),
        dataset_version=args.dataset_version,
        source_layer=args.source_layer,
        spatial_resolution=args.spatial_resolution,
        fields=HydrogeologyFieldMapping(
            record_id=args.record_id_field,
            geology=args.geology_field,
            lithology=args.lithology_field,
            geomorphology=args.geomorphology_field,
            groundwater_prospect=args.groundwater_prospect_field,
            aquifer_type=args.aquifer_type_field,
            aquifer_depth=args.aquifer_depth_field,
            aquifer_thickness=args.aquifer_thickness_field,
            aquifer_characteristics=dict(args.aquifer_characteristic),
        ),
    )
    OfficialHydrogeologyPolygonImporter.write(normalized, args.output)
    print(
        f"Imported {normalized['recordCount']} hydrogeology polygons into {args.output}"
    )


if __name__ == "__main__":
    main()
