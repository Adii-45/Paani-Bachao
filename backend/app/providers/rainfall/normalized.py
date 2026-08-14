from pathlib import Path

from ...domain.environment import RainfallLookup
from ...domain.location import NormalizedLocation
from ...provenance.models import DataStatus
from ...provenance.registry import source_registry
from ...repositories.rainfall import NormalizedRainfallRepository

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "normalized"
    / "imd_normal_annual_rainfall.json.gz"
)


class NormalizedImdRainfallProvider:
    """Reads a versioned local cache imported from an official IMD dataset.

    It uses the resolved coordinate and the official district polygons. It does not
    infer a nearest station or interpolate outside the published source geometry.
    """

    def __init__(self, dataset_path: Path = DEFAULT_DATASET_PATH) -> None:
        self.repository = NormalizedRainfallRepository(dataset_path)

    def lookup(self, location: NormalizedLocation) -> RainfallLookup:
        try:
            dataset = self.repository.load()
        except (FileNotFoundError, OSError, ValueError):
            return RainfallLookup(
                status=DataStatus.DATA_UNAVAILABLE,
                error_code="RAINFALL_DATA_UNAVAILABLE",
                message="RainfallDataUnavailable: the normalized IMD cache cannot be loaded.",
            )

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
                error_code="RAINFALL_DATA_UNAVAILABLE",
            )
        else:
            result_status = DataStatus.DATA_AVAILABLE

        records = [
            record
            for record in self.repository.records(dataset)
            if record.statistic_type == "LONG_PERIOD_NORMAL_ANNUAL"
        ]
        matches = self.repository.find_at_coordinates(
            records,
            latitude=location.latitude,
            longitude=location.longitude,
        )

        if not matches:
            return RainfallLookup(
                status=DataStatus.UNSUPPORTED_LOCATION,
                error_code="RAINFALL_DATA_UNAVAILABLE",
                message=(
                    "RainfallDataUnavailable: the resolved coordinate is not covered by "
                    "an imported IMD district-normal polygon."
                ),
            )
        if len(matches) > 1:
            return RainfallLookup(
                status=DataStatus.INSUFFICIENT_DATA,
                error_code="RAINFALL_LOCATION_AMBIGUOUS",
                message="More than one IMD district polygon contains this coordinate.",
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
