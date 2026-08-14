from pathlib import Path

from ..domain.ar_environment import SoilInformation, SoilLookup
from ..domain.location import NormalizedLocation
from ..provenance.models import DataStatus
from ..provenance.registry import source_registry
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

    def lookup(self, location: NormalizedLocation) -> SoilLookup:
        try:
            dataset = self.repository.load()
            records = self.repository.records(dataset, SoilInformation)
        except (FileNotFoundError, OSError, ValueError):
            return SoilLookup(
                status=DataStatus.PROVIDER_UNAVAILABLE,
                message="Soil provider cache could not be loaded.",
            )
        dataset_status = dataset.get("datasetStatus")
        if not records or dataset_status not in {"DATA_AVAILABLE", "DATA_STALE"}:
            return SoilLookup(
                status=DataStatus.DATA_UNAVAILABLE,
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
            and record.bounding_box[0] <= location.longitude <= record.bounding_box[2]
            and record.bounding_box[1] <= location.latitude <= record.bounding_box[3]
            and point_in_geometry(location.longitude, location.latitude, record.geometry)
        ]
        if len(matches) == 1:
            match = matches[0]
            if set(match.provenance.source_ids) - set(source_registry()):
                return SoilLookup(
                    status=DataStatus.PROVIDER_UNAVAILABLE,
                    message="Soil cache contains an unregistered source identifier.",
                )
            if not any(
                (
                    match.soil_class,
                    match.soil_texture,
                    match.permeability_class,
                    match.source_category,
                )
            ):
                return SoilLookup(
                    status=DataStatus.INSUFFICIENT_DATA,
                    information=match,
                    message=(
                        "An official soil polygon covers this coordinate, but the source "
                        "record contains no mapped soil classification. No value was inferred."
                    ),
                )
            return SoilLookup(
                status=(
                    DataStatus.DATA_STALE
                    if dataset_status == "DATA_STALE"
                    else DataStatus.DATA_AVAILABLE
                ),
                information=match,
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
            status=DataStatus.UNSUPPORTED_LOCATION,
            message=(
                "No reviewed soil polygon covers this "
                "coordinate. A field infiltration/percolation test is required."
            ),
        )
