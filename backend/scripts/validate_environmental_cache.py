"""Validate reviewed environmental caches before runtime use.

This command does not scrape government portals or invent missing fields. Upstream
exports must first be obtained through an official download/service and reviewed.
"""

import argparse
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.ar_environment import (
    GroundwaterObservation,
    HydrogeologyInformation,
    SoilInformation,
)
from app.provenance.registry import source_registry


MODELS = {
    "groundwater": GroundwaterObservation,
    "soil": SoilInformation,
    "hydrogeology": HydrogeologyInformation,
}


def validate_cache(path: Path, dataset_type: str) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    model = MODELS[dataset_type]
    registry = source_registry()
    records = payload.get("records", [])
    for item in records:
        record = model.model_validate(item)
        unknown = set(record.provenance.source_ids) - set(registry)
        if unknown:
            raise ValueError(f"Unknown source IDs: {sorted(unknown)}")
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_type", choices=sorted(MODELS))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    count = validate_cache(args.path, args.dataset_type)
    print(f"Validated {count} {args.dataset_type} records in {args.path}")


if __name__ == "__main__":
    main()
