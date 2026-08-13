import json
from pathlib import Path

from ...domain.environment import LocationQuery, RainfallLookup, RainfallRecord
from ...provenance.models import DataStatus
from ...provenance.registry import source_registry

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "normalized"
    / "imd_normal_annual_rainfall.json"
)


def normalize_location(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.casefold().replace(",", " ").split())


class NormalizedImdRainfallProvider:
    """Reads a versioned local cache imported from an official IMD dataset.

    It deliberately performs exact administrative/name matching. It does not infer a
    nearest station or interpolate a grid without source-defined geometry and method.
    """

    def __init__(self, dataset_path: Path = DEFAULT_DATASET_PATH) -> None:
        self.dataset_path = dataset_path

    def lookup(self, location: LocationQuery) -> RainfallLookup:
        with self.dataset_path.open(encoding="utf-8") as source:
            dataset = json.load(source)

        dataset_status = dataset.get("dataset_status")
        if dataset_status == "STALE":
            result_status = DataStatus.DATA_STALE
        elif dataset_status != "DATA_AVAILABLE":
            return RainfallLookup(
                status=DataStatus.DATA_UNAVAILABLE,
                message=(
                    "An official IMD long-period annual rainfall dataset has not been "
                    "ingested for this installation."
                ),
            )
        else:
            result_status = DataStatus.DATA_AVAILABLE

        requested_name = normalize_location(location.location)
        requested_state = normalize_location(location.state)
        requested_district = normalize_location(location.district)
        matches: list[RainfallRecord] = []
        for item in dataset.get("records", []):
            record = RainfallRecord.model_validate(item)
            if record.statistic_type != "LONG_PERIOD_NORMAL_ANNUAL":
                continue
            names = {
                normalize_location(record.location_name),
                normalize_location(record.district),
                record.record_id.casefold(),
            }
            if requested_name not in names:
                continue
            if requested_state and requested_state != normalize_location(record.state):
                continue
            if requested_district and requested_district != normalize_location(record.district):
                continue
            matches.append(record)

        if not matches:
            return RainfallLookup(
                status=DataStatus.UNSUPPORTED_LOCATION,
                message="No matching official annual-normal rainfall record is available.",
            )
        if len(matches) > 1:
            return RainfallLookup(
                status=DataStatus.INSUFFICIENT_DATA,
                message="The location is ambiguous; provide state and district identifiers.",
            )

        record = matches[0]
        if record.source_id not in source_registry():
            raise RuntimeError(f"Rainfall record uses unknown source ID: {record.source_id}")
        message = (
            "Official rainfall record is available."
            if result_status is DataStatus.DATA_AVAILABLE
            else "A stale official rainfall cache is available; review its dataset version."
        )
        return RainfallLookup(status=result_status, record=record, message=message)
