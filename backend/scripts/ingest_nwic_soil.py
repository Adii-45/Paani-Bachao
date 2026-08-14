"""Normalize a reviewed official NWIC soil polygon GeoJSON export."""

import argparse
from datetime import UTC, datetime
from pathlib import Path

from app.importers.nwic_soil import (
    NWICSoilFieldMapping,
    NWICSoilPolygonImporter,
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "data"
    / "normalized"
    / "official_soil_information.json"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--source-layer", required=True)
    parser.add_argument("--spatial-resolution", required=True)
    parser.add_argument("--record-id-field", required=True)
    parser.add_argument("--soil-class-field")
    parser.add_argument("--soil-texture-field")
    parser.add_argument("--permeability-class-field")
    parser.add_argument("--source-category-field")
    parser.add_argument("--source-code-field")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--confirm-official-source", action="store_true")
    args = parser.parse_args()
    if not args.confirm_official_source:
        parser.error("--confirm-official-source is required")

    normalized = NWICSoilPolygonImporter().normalize(
        args.source.read_text(encoding="utf-8-sig"),
        imported_at=datetime.now(UTC),
        dataset_version=args.dataset_version,
        source_layer=args.source_layer,
        spatial_resolution=args.spatial_resolution,
        fields=NWICSoilFieldMapping(
            record_id=args.record_id_field,
            soil_class=args.soil_class_field,
            soil_texture=args.soil_texture_field,
            permeability_class=args.permeability_class_field,
            source_category=args.source_category_field,
            source_code=args.source_code_field,
        ),
    )
    NWICSoilPolygonImporter.write(normalized, args.output)
    print(f"Imported {normalized['recordCount']} soil polygons into {args.output}")


if __name__ == "__main__":
    main()
