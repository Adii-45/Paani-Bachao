from datetime import UTC
from pathlib import Path

from ..domain.ar_environment import (
    EnvironmentalResolution,
    HydrogeologyInformation,
    HydrogeologyLookup,
)
from ..domain.location import NormalizedLocation
from ..provenance.models import DataQuality, DataStatus, ValueProvenance
from ..provenance.registry import source_registry
from ..repositories.environmental import NormalizedEnvironmentalRepository
from ..repositories.rainfall import point_in_geometry

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "normalized"
    / "official_hydrogeology_information.json"
)


def _component_status(
    records: list[HydrogeologyInformation], *, stale: bool
) -> DataStatus:
    if not records:
        return DataStatus.DATA_UNAVAILABLE
    if len(records) > 1:
        return DataStatus.INSUFFICIENT_DATA
    return DataStatus.DATA_STALE if stale else DataStatus.DATA_AVAILABLE


class NormalizedOfficialHydrogeologyProvider:
    def __init__(self, dataset_path: Path = DEFAULT_DATASET_PATH) -> None:
        self.repository = NormalizedEnvironmentalRepository(dataset_path)

    def lookup(self, location: NormalizedLocation) -> HydrogeologyLookup:
        try:
            dataset = self.repository.load()
            records = self.repository.records(dataset, HydrogeologyInformation)
        except (FileNotFoundError, OSError, ValueError):
            return self._unavailable(DataStatus.PROVIDER_UNAVAILABLE)
        dataset_status = dataset.get("datasetStatus")
        if not records or dataset_status not in {"DATA_AVAILABLE", "DATA_STALE"}:
            return self._unavailable(DataStatus.DATA_UNAVAILABLE)
        matches = sorted(
            (
                record
                for record in records
                if record.bounding_box is not None
                and record.geometry is not None
                and record.bounding_box[0]
                <= location.longitude
                <= record.bounding_box[2]
                and record.bounding_box[1]
                <= location.latitude
                <= record.bounding_box[3]
                and point_in_geometry(
                    location.longitude, location.latitude, record.geometry
                )
            ),
            key=lambda record: record.record_id,
        )
        if not matches:
            return self._unavailable(DataStatus.UNSUPPORTED_LOCATION)
        if any(
            set(record.provenance.source_ids) - set(source_registry())
            for record in matches
        ):
            return self._unavailable(DataStatus.PROVIDER_UNAVAILABLE)

        geology_records = [
            record for record in matches if record.geology or record.lithology
        ]
        geomorphology_records = [record for record in matches if record.geomorphology]
        aquifer_records = [
            record
            for record in matches
            if record.aquifer_type
            or record.aquifer_depth
            or record.aquifer_thickness
            or record.aquifer_characteristics
        ]
        prospect_records = [
            record for record in matches if record.groundwater_prospect
        ]
        stale = dataset_status == "DATA_STALE"
        geology_status = _component_status(geology_records, stale=stale)
        geomorphology_status = _component_status(geomorphology_records, stale=stale)
        aquifer_status = _component_status(aquifer_records, stale=stale)
        prospect_status = _component_status(prospect_records, stale=stale)
        statuses = (
            geology_status,
            geomorphology_status,
            aquifer_status,
            prospect_status,
        )
        all_resolved = all(
            status in {DataStatus.DATA_AVAILABLE, DataStatus.DATA_STALE}
            for status in statuses
        )
        information = self._compose(
            geology_records=geology_records,
            geomorphology_records=geomorphology_records,
            aquifer_records=aquifer_records,
            prospect_records=prospect_records,
        )
        ambiguous_components = [
            label
            for label, component_records in (
                ("geology/lithology", geology_records),
                ("geomorphology", geomorphology_records),
                ("aquifer", aquifer_records),
                ("groundwater prospect", prospect_records),
            )
            if len(component_records) > 1
        ]
        return HydrogeologyLookup(
            status=(
                DataStatus.DATA_STALE
                if all_resolved and stale
                else DataStatus.DATA_AVAILABLE
                if all_resolved
                else DataStatus.INSUFFICIENT_DATA
            ),
            information=information,
            features=matches,
            geologyStatus=geology_status,
            geomorphologyStatus=geomorphology_status,
            aquiferStatus=aquifer_status,
            groundwaterProspectStatus=prospect_status,
            message=(
                "Multiple intersecting source features conflict for: "
                + ", ".join(ambiguous_components)
                + ". Source features are returned separately; no value was selected."
                if ambiguous_components
                else "Reviewed regional source features intersect the coordinate. "
                "Component statuses identify which attributes are available; missing "
                "properties remain unknown."
            ),
        )

    @staticmethod
    def _compose(
        *,
        geology_records: list[HydrogeologyInformation],
        geomorphology_records: list[HydrogeologyInformation],
        aquifer_records: list[HydrogeologyInformation],
        prospect_records: list[HydrogeologyInformation],
    ) -> HydrogeologyInformation | None:
        resolved_records = [
            records[0]
            for records in (
                geology_records,
                geomorphology_records,
                aquifer_records,
                prospect_records,
            )
            if len(records) == 1
        ]
        if not resolved_records:
            return None
        geology = geology_records[0] if len(geology_records) == 1 else None
        geomorphology = (
            geomorphology_records[0] if len(geomorphology_records) == 1 else None
        )
        aquifer = aquifer_records[0] if len(aquifer_records) == 1 else None
        prospect = prospect_records[0] if len(prospect_records) == 1 else None
        source_ids = sorted(
            {
                source_id
                for record in resolved_records
                for source_id in record.provenance.source_ids
            }
        )
        retrieved_times = [
            record.provenance.retrieved_at
            for record in resolved_records
            if record.provenance.retrieved_at is not None
        ]
        return HydrogeologyInformation(
            recordId=(
                "composed:"
                + "+".join(record.record_id for record in resolved_records)
            ),
            geology=geology.geology if geology else None,
            lithology=geology.lithology if geology else None,
            geomorphology=(geomorphology.geomorphology if geomorphology else None),
            groundwaterProspect=(
                prospect.groundwater_prospect if prospect else None
            ),
            aquiferType=aquifer.aquifer_type if aquifer else None,
            aquiferDepth=aquifer.aquifer_depth if aquifer else None,
            aquiferThickness=aquifer.aquifer_thickness if aquifer else None,
            aquiferCharacteristics=(
                aquifer.aquifer_characteristics if aquifer else {}
            ),
            spatialResolution=EnvironmentalResolution.REGIONAL_LAYER,
            datasetVersion="; ".join(
                sorted({record.dataset_version for record in resolved_records})
            ),
            provenance=ValueProvenance(
                quality=DataQuality.DERIVED,
                sourceIds=source_ids,
                sourceRecord="; ".join(
                    record.provenance.source_record or record.record_id
                    for record in resolved_records
                ),
                sourceDateOrVersion="; ".join(
                    sorted({record.dataset_version for record in resolved_records})
                ),
                spatialResolution="composed from intersecting regional source polygons",
                retrievedAt=(
                    max(retrieved_times).astimezone(UTC)
                    if retrieved_times
                    else None
                ),
                notes=(
                    "Response composition only; each original source feature is preserved "
                    "in the features array. No missing attribute or recharge score is inferred."
                ),
            ),
        )

    @staticmethod
    def _unavailable(status: DataStatus) -> HydrogeologyLookup:
        return HydrogeologyLookup(
            status=status,
            features=[],
            geologyStatus=status,
            geomorphologyStatus=status,
            aquiferStatus=status,
            groundwaterProspectStatus=status,
            message=(
                "No reviewed coordinate-level geology/geomorphology/aquifer feature is "
                "available. NWIC/Bhuvan service metadata alone are not treated as site data."
            ),
        )
