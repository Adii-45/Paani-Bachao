"""Normalize an officially obtained IMD annual-normal rainfall CSV.

This script does not download data and does not infer missing metadata. The operator
must verify licensing and authenticity, then explicitly confirm the source.
"""

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.environment import RainfallRecord
from app.provenance.registry import source_registry

REQUIRED_COLUMNS = {
    "record_id",
    "location_name",
    "rainfall_mm",
    "reference_period",
    "spatial_resolution",
    "source_record",
}


def optional_float(value: str | None) -> float | None:
    return float(value) if value and value.strip() else None


def normalize_csv(
    input_path: Path,
    *,
    dataset_title: str,
    dataset_version: str,
    source_id: str,
    retrieved_at: datetime,
) -> dict[str, object]:
    if source_id not in source_registry():
        raise ValueError(f"Unknown source ID: {source_id}")
    with input_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Missing required CSV columns: {', '.join(sorted(missing))}")
        records = []
        for row in reader:
            record = RainfallRecord(
                recordId=row["record_id"],
                locationName=row["location_name"],
                state=row.get("state") or None,
                district=row.get("district") or None,
                latitude=optional_float(row.get("latitude")),
                longitude=optional_float(row.get("longitude")),
                rainfallMm=float(row["rainfall_mm"]),
                statisticType="LONG_PERIOD_NORMAL_ANNUAL",
                referencePeriod=row["reference_period"],
                spatialResolution=row["spatial_resolution"],
                sourceId=source_id,
                sourceRecord=row["source_record"],
                datasetVersion=dataset_version,
                retrievedAt=retrieved_at,
            )
            records.append(record.model_dump(mode="json", by_alias=False))
    return {
        "dataset_status": "DATA_AVAILABLE",
        "source_id": source_id,
        "dataset_title": dataset_title,
        "dataset_version": dataset_version,
        "imported_at": retrieved_at.isoformat(),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--dataset-title", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--source-id", default="IMD_NORMAL_RAINFALL_DATASET")
    parser.add_argument("--confirm-official-source", action="store_true")
    args = parser.parse_args()
    if not args.confirm_official_source:
        parser.error("--confirm-official-source is required after verifying the dataset")

    retrieved_at = datetime.now(UTC)
    normalized = normalize_csv(
        args.input_csv,
        dataset_title=args.dataset_title,
        dataset_version=args.dataset_version,
        source_id=args.source_id,
        retrieved_at=retrieved_at,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
