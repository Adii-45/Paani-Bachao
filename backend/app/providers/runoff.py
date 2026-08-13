import json
from pathlib import Path

from ..domain.environment import RunoffCoefficientLookup, RunoffCoefficientRecord
from ..provenance.models import DataStatus
from ..provenance.registry import source_registry

DEFAULT_COEFFICIENT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "source_backed"
    / "runoff_coefficients.json"
)


class SourceBackedRunoffCoefficientProvider:
    def __init__(self, data_path: Path = DEFAULT_COEFFICIENT_PATH) -> None:
        self.data_path = data_path

    def lookup(self, roof_type: str) -> RunoffCoefficientLookup:
        with self.data_path.open(encoding="utf-8") as source:
            dataset = json.load(source)
        if dataset.get("dataset_status") != "DATA_AVAILABLE":
            return RunoffCoefficientLookup(
                status=DataStatus.DATA_UNAVAILABLE,
                message=(
                    "A source-backed runoff coefficient is not configured for this roof type."
                ),
            )

        matches = [
            RunoffCoefficientRecord.model_validate(item)
            for item in dataset.get("records", [])
            if item.get("roof_type") == roof_type or item.get("roofType") == roof_type
        ]
        if len(matches) != 1:
            return RunoffCoefficientLookup(
                status=DataStatus.DATA_UNAVAILABLE,
                message=(
                    "A unique source-backed runoff coefficient is not configured for this "
                    "roof type and condition."
                ),
            )
        record = matches[0]
        for source_id in record.source_ids:
            if source_id not in source_registry():
                raise RuntimeError(f"Runoff record uses unknown source ID: {source_id}")
        if record.value_range.selected_value is None:
            return RunoffCoefficientLookup(
                status=DataStatus.INSUFFICIENT_DATA,
                record=record,
                message=(
                    "The source publishes a coefficient range, but the available property "
                    "information does not justify selecting one value."
                ),
            )
        return RunoffCoefficientLookup(
            status=DataStatus.DATA_AVAILABLE,
            record=record,
            message="A source-backed runoff coefficient is available.",
        )
