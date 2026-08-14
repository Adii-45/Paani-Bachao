from pathlib import Path

from ..domain.ar_environment import SoilInformation, SoilLookup
from ..domain.location import NormalizedLocation
from ..provenance.models import DataStatus
from ..repositories.environmental import NormalizedEnvironmentalRepository
from ..repositories.rainfall import point_in_geometry

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "normalized"
    / "official_soil_information.json"
)


class NormalizedOfficialSoilProvider:
    def __init__(self, dataset_path: Path = DEFAULT_DATASET_PATH) -> None:
        self.repository = NormalizedEnvironmentalRepository(dataset_path)

    def lookup(self, _location: NormalizedLocation) -> SoilLookup:
        try:
            dataset = self.repository.load()
            records = self.repository.records(dataset, SoilInformation)
        except (FileNotFoundError, OSError, ValueError):
            return SoilLookup(
                status=DataStatus.PROVIDER_UNAVAILABLE,
                message="Soil provider cache could not be loaded.",
            )
        if not records:
            return SoilLookup(
                status=DataStatus.FIELD_MEASUREMENT_REQUIRED,
                message=(
                    "No reviewed coordinate-level official soil feature is imported. "
                    "A field infiltration/percolation test is required before design."
                ),
            )
        matches = [
            record
            for record in records
            if record.bounding_box is not None
            and record.geometry is not None
            and record.bounding_box[0] <= _location.longitude <= record.bounding_box[2]
            and record.bounding_box[1] <= _location.latitude <= record.bounding_box[3]
            and point_in_geometry(
                _location.longitude, _location.latitude, record.geometry
            )
        ]
        if len(matches) == 1:
            return SoilLookup(
                status=DataStatus.DATA_AVAILABLE,
                information=matches[0],
                message=(
                    "Regional official soil information is available. It is a proxy, "
                    "not a measured property infiltration rate; a field test is recommended."
                ),
            )
        if len(matches) > 1:
            return SoilLookup(
                status=DataStatus.INSUFFICIENT_DATA,
                message="Multiple official soil polygons contain this coordinate.",
            )
        return SoilLookup(
            status=DataStatus.FIELD_MEASUREMENT_REQUIRED,
            message=(
                "No reviewed soil polygon covers this "
                "coordinate. A field infiltration/percolation test is required."
            ),
        )
