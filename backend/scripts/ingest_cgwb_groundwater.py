"""Normalize reviewed CGWB groundwater observations and station coordinates."""

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path

from app.importers.cgwb_groundwater import CGWBGroundwaterImporter
from app.provenance.models import DataStatus

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "data"
    / "normalized"
    / "cgwb_groundwater_observations.json"
)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--stations", type=Path, required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument(
        "--dataset-status",
        required=True,
        choices=(DataStatus.DATA_AVAILABLE.value, DataStatus.DATA_STALE.value),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--confirm-official-sources", action="store_true")
    args = parser.parse_args()
    if not args.confirm_official_sources:
        parser.error("--confirm-official-sources is required")

    normalized = CGWBGroundwaterImporter().normalize(
        _rows(args.observations),
        _rows(args.stations),
        imported_at=datetime.now(UTC),
        dataset_status=DataStatus(args.dataset_status),
        dataset_version=args.dataset_version,
    )
    CGWBGroundwaterImporter.write(normalized, args.output)
    print(f"Imported {normalized['recordCount']} groundwater observations into {args.output}")


if __name__ == "__main__":
    main()
