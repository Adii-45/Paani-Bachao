import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from ..importers.spatial import validated_polygon_geometry


RecordT = TypeVar("RecordT", bound=BaseModel)


class NormalizedEnvironmentalRepository:
    """Read a reviewed, versioned environmental cache.

    Runtime assessment code never contacts the upstream government service. Cache
    refresh and review are separate operational steps.
    """

    def __init__(self, dataset_path: Path) -> None:
        self.dataset_path = dataset_path

    def load(self) -> dict[str, Any]:
        with self.dataset_path.open(encoding="utf-8") as source:
            return json.load(source)

    @staticmethod
    def records(dataset: dict[str, Any], model: type[RecordT]) -> list[RecordT]:
        records = [model.model_validate(item) for item in dataset.get("records", [])]
        for record in records:
            geometry = getattr(record, "geometry", None)
            bounding_box = getattr(record, "bounding_box", None)
            if geometry is None and bounding_box is None:
                continue
            if geometry is None or bounding_box is None:
                raise ValueError(
                    "Spatial cache records require both geometry and bounding box."
                )
            _, calculated_box = validated_polygon_geometry(geometry)
            if any(
                abs(expected - actual) > 1e-8
                for expected, actual in zip(
                    bounding_box, calculated_box, strict=True
                )
            ):
                raise ValueError("Spatial cache bounding box does not match geometry.")
        return records
