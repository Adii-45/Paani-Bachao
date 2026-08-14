import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel


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
        return [model.model_validate(item) for item in dataset.get("records", [])]
