from pathlib import Path

from ..domain.ar_environment import HydrogeologyInformation, HydrogeologyLookup
from ..domain.location import NormalizedLocation
from ..provenance.models import DataStatus
from ..repositories.environmental import NormalizedEnvironmentalRepository
from ..repositories.rainfall import point_in_geometry

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "normalized"
    / "official_hydrogeology_information.json"
)


class NormalizedOfficialHydrogeologyProvider:
    def __init__(self, dataset_path: Path = DEFAULT_DATASET_PATH) -> None:
        self.repository = NormalizedEnvironmentalRepository(dataset_path)

    def lookup(self, _location: NormalizedLocation) -> HydrogeologyLookup:
        try:
            dataset = self.repository.load()
            records = self.repository.records(dataset, HydrogeologyInformation)
        except (FileNotFoundError, OSError, ValueError):
            return self._unavailable(DataStatus.PROVIDER_UNAVAILABLE)
        if not records:
            return self._unavailable(DataStatus.DATA_UNAVAILABLE)
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
        if len(matches) > 1:
            return self._unavailable(DataStatus.INSUFFICIENT_DATA)
        if not matches:
            return self._unavailable(DataStatus.UNSUPPORTED_LOCATION)

        information = matches[0]
        geology_status = (
            DataStatus.DATA_AVAILABLE
            if information.geology or information.lithology
            else DataStatus.DATA_UNAVAILABLE
        )
        geomorphology_status = (
            DataStatus.DATA_AVAILABLE
            if information.geomorphology
            else DataStatus.DATA_UNAVAILABLE
        )
        aquifer_status = (
            DataStatus.DATA_AVAILABLE
            if information.aquifer_type
            else DataStatus.DATA_UNAVAILABLE
        )
        prospect_status = (
            DataStatus.DATA_AVAILABLE
            if information.groundwater_prospect
            else DataStatus.DATA_UNAVAILABLE
        )
        all_available = all(
            status is DataStatus.DATA_AVAILABLE
            for status in (
                geology_status,
                geomorphology_status,
                aquifer_status,
                prospect_status,
            )
        )
        return HydrogeologyLookup(
            status=(
                DataStatus.DATA_AVAILABLE
                if all_available
                else DataStatus.INSUFFICIENT_DATA
            ),
            information=information,
            geologyStatus=geology_status,
            geomorphologyStatus=geomorphology_status,
            aquiferStatus=aquifer_status,
            groundwaterProspectStatus=prospect_status,
            message=(
                "A reviewed regional hydrogeology feature intersects the coordinate. "
                "Component statuses show which source attributes are actually populated."
            ),
        )

    @staticmethod
    def _unavailable(status: DataStatus) -> HydrogeologyLookup:
        return HydrogeologyLookup(
            status=status,
            geologyStatus=status,
            geomorphologyStatus=status,
            aquiferStatus=status,
            groundwaterProspectStatus=status,
            message=(
                "No reviewed coordinate-level geology/geomorphology/aquifer feature is "
                "available. NWIC/Bhuvan service metadata alone are not treated as site data."
            ),
        )
