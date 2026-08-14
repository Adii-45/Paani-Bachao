import gzip
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from ..domain.ar_environment import (
    GroundwaterObservation,
    HydrogeologyInformation,
    SoilInformation,
)
from ..domain.environment import RainfallRecord
from ..domain.environmental_validation import (
    CacheValidationStatus,
    EnvironmentalCacheReport,
    EnvironmentalCoverage,
    EnvironmentalDataset,
    EnvironmentalValidationSummary,
)
from ..importers.spatial import validated_polygon_geometry
from ..provenance.models import DataStatus
from ..provenance.registry import source_registry
from ..providers.groundwater import DEFAULT_DATASET_PATH as GROUNDWATER_PATH
from ..providers.hydrogeology import DEFAULT_DATASET_PATH as HYDROGEOLOGY_PATH
from ..providers.rainfall.normalized import DEFAULT_DATASET_PATH as RAINFALL_PATH
from ..providers.soil import DEFAULT_DATASET_PATH as SOIL_PATH

DATASET_MODELS: dict[EnvironmentalDataset, type[BaseModel]] = {
    EnvironmentalDataset.RAINFALL: RainfallRecord,
    EnvironmentalDataset.GROUNDWATER: GroundwaterObservation,
    EnvironmentalDataset.SOIL: SoilInformation,
    EnvironmentalDataset.HYDROGEOLOGY: HydrogeologyInformation,
}

DEFAULT_CACHE_PATHS = {
    EnvironmentalDataset.RAINFALL: RAINFALL_PATH,
    EnvironmentalDataset.GROUNDWATER: GROUNDWATER_PATH,
    EnvironmentalDataset.SOIL: SOIL_PATH,
    EnvironmentalDataset.HYDROGEOLOGY: HYDROGEOLOGY_PATH,
}

FRESHNESS_DESCRIPTIONS = {
    EnvironmentalDataset.RAINFALL: (
        "Long-period rainfall normals follow their published reference period and "
        "operator-declared dataset status; no daily refresh interval is assumed."
    ),
    EnvironmentalDataset.GROUNDWATER: (
        "Seasonal observation freshness follows the reviewed cache status and latest "
        "observation date; no maximum age is assumed unless explicitly configured."
    ),
    EnvironmentalDataset.SOIL: (
        "Regional soil maps follow their published dataset version and operator-declared "
        "status; no daily refresh interval is assumed."
    ),
    EnvironmentalDataset.HYDROGEOLOGY: (
        "Regional geology/aquifer layers follow their published version and operator-"
        "declared status; no daily refresh interval is assumed."
    ),
}


@dataclass(frozen=True)
class EnvironmentalFreshnessConfig:
    rainfall_max_age_days: int | None = None
    groundwater_max_age_days: int | None = None
    soil_max_age_days: int | None = None
    hydrogeology_max_age_days: int | None = None

    def maximum_age(self, dataset: EnvironmentalDataset) -> int | None:
        value = {
            EnvironmentalDataset.RAINFALL: self.rainfall_max_age_days,
            EnvironmentalDataset.GROUNDWATER: self.groundwater_max_age_days,
            EnvironmentalDataset.SOIL: self.soil_max_age_days,
            EnvironmentalDataset.HYDROGEOLOGY: self.hydrogeology_max_age_days,
        }[dataset]
        if value is not None and value <= 0:
            raise ValueError("Configured environmental cache ages must be positive.")
        return value


def _metadata(payload: dict[str, Any], snake: str, camel: str) -> Any:
    return payload.get(snake, payload.get(camel))


def _load_payload(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, mode="rt", encoding="utf-8") as source:
            payload = json.load(source)
    else:
        with path.open(encoding="utf-8") as source:
            payload = json.load(source)
    if not isinstance(payload, dict):
        raise ValueError("Cache root must be a JSON object.")
    return payload


def _parse_imported_at(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Imported timestamp must be an ISO-8601 string.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Imported timestamp must include a timezone.")
    return parsed.astimezone(UTC)


def _record_issue(index: int, error: Exception) -> str:
    if isinstance(error, ValidationError) and error.errors():
        detail = error.errors()[0]
        location = ".".join(str(item) for item in detail.get("loc", ()))
        return f"Record {index}: {location}: {detail.get('msg', 'invalid value')}."
    return f"Record {index}: {error}."


def _source_ids(
    dataset: EnvironmentalDataset, record: BaseModel
) -> tuple[list[str], list[str]]:
    if dataset is EnvironmentalDataset.RAINFALL:
        rainfall = record
        return [rainfall.source_id], [rainfall.source_name]  # type: ignore[attr-defined]
    provenance = record.provenance  # type: ignore[attr-defined]
    ids = list(provenance.source_ids)
    registry = source_registry()
    names = [registry[source_id].authority for source_id in ids if source_id in registry]
    return ids, names


def _validate_record(
    dataset: EnvironmentalDataset, index: int, item: Any
) -> BaseModel:
    model = DATASET_MODELS[dataset]
    record = model.model_validate(item)
    ids, _ = _source_ids(dataset, record)
    if not ids:
        raise ValueError("Source provenance is missing.")
    unknown = set(ids) - set(source_registry())
    if unknown:
        raise ValueError(f"Unknown source IDs: {sorted(unknown)}.")
    if dataset in {
        EnvironmentalDataset.RAINFALL,
        EnvironmentalDataset.SOIL,
        EnvironmentalDataset.HYDROGEOLOGY,
    }:
        geometry = record.geometry  # type: ignore[attr-defined]
        bounding_box = record.bounding_box  # type: ignore[attr-defined]
        if geometry is None or bounding_box is None:
            raise ValueError("Provider-ready polygon geometry and bounding box are required.")
        _, calculated_box = validated_polygon_geometry(geometry)
        if any(
            abs(expected - actual) > 1e-8
            for expected, actual in zip(bounding_box, calculated_box, strict=True)
        ):
            raise ValueError("Bounding box does not match polygon geometry.")
    return record


def _coverage(records: list[BaseModel]) -> EnvironmentalCoverage | None:
    if not records:
        return None
    boxes: list[tuple[float, float, float, float]] = []
    states: set[str] = set()
    districts: set[str] = set()
    resolutions: set[str] = set()
    for record in records:
        bounding_box = getattr(record, "bounding_box", None)
        if bounding_box is not None:
            boxes.append(bounding_box)
        else:
            latitude = getattr(record, "latitude", None)
            longitude = getattr(record, "longitude", None)
            if latitude is not None and longitude is not None:
                boxes.append((longitude, latitude, longitude, latitude))
        if state := getattr(record, "state", None):
            states.add(state)
        if district := getattr(record, "district", None):
            districts.add(district)
        resolution = getattr(record, "spatial_resolution", None)
        if resolution is not None:
            resolutions.add(getattr(resolution, "value", str(resolution)))
    bounding_box = None
    if boxes:
        bounding_box = (
            min(box[0] for box in boxes),
            min(box[1] for box in boxes),
            max(box[2] for box in boxes),
            max(box[3] for box in boxes),
        )
    return EnvironmentalCoverage(
        boundingBox=bounding_box,
        states=sorted(states),
        districts=sorted(districts),
        spatialResolutions=sorted(resolutions),
    )


def _period_metadata(
    dataset: EnvironmentalDataset, records: list[BaseModel]
) -> tuple[str | None, date | None]:
    if dataset is EnvironmentalDataset.RAINFALL:
        periods = sorted(
            {
                record.reference_period  # type: ignore[attr-defined]
                for record in records
            }
        )
        return "; ".join(periods) or None, None
    if dataset is EnvironmentalDataset.GROUNDWATER:
        dates = sorted(
            record.observation_date  # type: ignore[attr-defined]
            for record in records
            if record.observation_date is not None  # type: ignore[attr-defined]
        )
        if dates:
            return f"{dates[0].isoformat()} to {dates[-1].isoformat()}", dates[-1]
        periods = sorted(
            {
                record.observation_period  # type: ignore[attr-defined]
                for record in records
                if record.observation_period  # type: ignore[attr-defined]
            }
        )
        if periods:
            return "; ".join(periods), None
    return None, None


def _component_counts(
    dataset: EnvironmentalDataset, records: list[BaseModel]
) -> dict[str, int]:
    if dataset is EnvironmentalDataset.RAINFALL:
        return {
            "annualRainfall": sum(
                getattr(record, "rainfall_mm", None) is not None for record in records
            ),
            "monthlyNormals": sum(
                getattr(record, "monthly_normal", None) is not None for record in records
            ),
        }
    if dataset is EnvironmentalDataset.GROUNDWATER:
        return {"datedDepthObservations": len(records)}
    if dataset is EnvironmentalDataset.SOIL:
        return {
            "soilClass": sum(bool(getattr(record, "soil_class", None)) for record in records),
            "soilTexture": sum(
                bool(getattr(record, "soil_texture", None)) for record in records
            ),
            "measuredInfiltration": sum(
                getattr(record, "measured_infiltration_rate_mm_per_hr", None)
                is not None
                for record in records
            ),
        }
    return {
        "geologyOrLithology": sum(
            bool(getattr(record, "geology", None) or getattr(record, "lithology", None))
            for record in records
        ),
        "geomorphology": sum(
            bool(getattr(record, "geomorphology", None)) for record in records
        ),
        "aquifer": sum(
            bool(
                getattr(record, "aquifer_type", None)
                or getattr(record, "aquifer_characteristics", None)
            )
            for record in records
        ),
        "groundwaterProspect": sum(
            bool(getattr(record, "groundwater_prospect", None)) for record in records
        ),
    }


class EnvironmentalCacheValidator:
    def __init__(
        self,
        *,
        paths: dict[EnvironmentalDataset, Path] | None = None,
        freshness: EnvironmentalFreshnessConfig | None = None,
        as_of: datetime | None = None,
    ) -> None:
        self.paths = paths or DEFAULT_CACHE_PATHS
        self.freshness = freshness or EnvironmentalFreshnessConfig()
        self.as_of = (as_of or datetime.now(UTC)).astimezone(UTC)

    def validate(self, dataset: EnvironmentalDataset) -> EnvironmentalCacheReport:
        path = self.paths[dataset]
        policy = FRESHNESS_DESCRIPTIONS[dataset]
        if not path.is_file():
            return EnvironmentalCacheReport(
                dataset=dataset,
                status=CacheValidationStatus.MISSING,
                providerStatus=self._failure_status(dataset, malformed=True),
                usable=False,
                freshnessPolicy=policy,
                issues=["Dataset file is missing."],
            )
        try:
            payload = _load_payload(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return EnvironmentalCacheReport(
                dataset=dataset,
                status=CacheValidationStatus.MALFORMED,
                providerStatus=self._failure_status(dataset, malformed=True),
                usable=False,
                freshnessPolicy=policy,
                issues=[f"Dataset cannot be parsed: {exc}."],
            )

        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            return EnvironmentalCacheReport(
                dataset=dataset,
                status=CacheValidationStatus.UNSUPPORTED_METADATA,
                providerStatus=DataStatus.DATA_UNAVAILABLE,
                usable=False,
                freshnessPolicy=policy,
                issues=["Dataset records metadata must be an array."],
            )
        issues: list[str] = []
        valid_records: list[BaseModel] = []
        for index, item in enumerate(raw_records):
            try:
                valid_records.append(_validate_record(dataset, index, item))
            except (ValueError, ValidationError, TypeError) as exc:
                issues.append(_record_issue(index, exc))

        declared_status = _metadata(payload, "dataset_status", "datasetStatus")
        version = _metadata(payload, "dataset_version", "datasetVersion")
        try:
            imported_at = _parse_imported_at(
                _metadata(payload, "imported_at", "importedAt")
            )
        except ValueError as exc:
            imported_at = None
            issues.append(str(exc))
        metadata_issues: list[str] = []
        recognized_statuses = {
            "DATA_AVAILABLE",
            "DATA_STALE",
            "STALE",
            "DATA_UNAVAILABLE",
        }
        if declared_status not in recognized_statuses:
            metadata_issues.append("Dataset status is missing or unsupported.")
        if raw_records and declared_status == "DATA_UNAVAILABLE":
            metadata_issues.append(
                "Dataset contains records but declares itself unavailable."
            )
        if not raw_records and declared_status in {
            "DATA_AVAILABLE",
            "DATA_STALE",
            "STALE",
        }:
            issues.append("Dataset declares availability but contains no records.")
        if raw_records and (not isinstance(version, str) or not version.strip()):
            metadata_issues.append("Dataset version is required when records exist.")
        if raw_records and imported_at is None:
            metadata_issues.append("Imported timestamp is required when records exist.")
        declared_count = _metadata(payload, "record_count", "recordCount")
        if declared_count is not None and declared_count != len(raw_records):
            metadata_issues.append("Declared record count does not match the cache.")
        issues.extend(metadata_issues)

        all_source_ids: set[str] = set()
        all_source_names: set[str] = set()
        for record in valid_records:
            ids, names = _source_ids(dataset, record)
            all_source_ids.update(ids)
            all_source_names.update(names)
        observation_period, latest_observation = _period_metadata(
            dataset, valid_records
        )
        invalid_count = len(raw_records) - len(valid_records)
        if invalid_count and valid_records:
            status = CacheValidationStatus.PARTIAL
        elif invalid_count:
            status = CacheValidationStatus.MALFORMED
        elif metadata_issues:
            status = CacheValidationStatus.UNSUPPORTED_METADATA
        elif not raw_records:
            status = CacheValidationStatus.EMPTY
        else:
            status = CacheValidationStatus.AVAILABLE

        if status is CacheValidationStatus.AVAILABLE:
            maximum_age = self.freshness.maximum_age(dataset)
            freshness_anchor = (
                datetime.combine(latest_observation, datetime.min.time(), tzinfo=UTC)
                if dataset is EnvironmentalDataset.GROUNDWATER
                and latest_observation is not None
                else imported_at
            )
            explicitly_stale = declared_status in {"DATA_STALE", "STALE"}
            configured_stale = (
                maximum_age is not None
                and freshness_anchor is not None
                and self.as_of - freshness_anchor > timedelta(days=maximum_age)
            )
            if explicitly_stale or configured_stale:
                status = CacheValidationStatus.STALE
                if configured_stale and not explicitly_stale:
                    issues.append(
                        "Dataset exceeds the explicitly configured maximum age."
                    )

        usable = status in {
            CacheValidationStatus.AVAILABLE,
            CacheValidationStatus.STALE,
        }
        provider_status = {
            CacheValidationStatus.AVAILABLE: DataStatus.DATA_AVAILABLE,
            CacheValidationStatus.STALE: DataStatus.DATA_STALE,
            CacheValidationStatus.EMPTY: DataStatus.DATA_UNAVAILABLE,
            CacheValidationStatus.UNSUPPORTED_METADATA: DataStatus.DATA_UNAVAILABLE,
            CacheValidationStatus.PARTIAL: self._failure_status(
                dataset, malformed=True
            ),
            CacheValidationStatus.MALFORMED: self._failure_status(
                dataset, malformed=True
            ),
            CacheValidationStatus.MISSING: self._failure_status(
                dataset, malformed=True
            ),
        }[status]
        return EnvironmentalCacheReport(
            dataset=dataset,
            status=status,
            providerStatus=provider_status,
            usable=usable,
            recordCount=len(raw_records),
            validRecordCount=len(valid_records),
            invalidRecordCount=invalid_count,
            sourceIds=sorted(all_source_ids),
            sourceNames=sorted(all_source_names),
            datasetVersion=version if isinstance(version, str) else None,
            importedAt=imported_at,
            observationPeriod=observation_period,
            latestObservationDate=latest_observation,
            freshnessPolicy=policy,
            coverage=_coverage(valid_records),
            componentCounts=_component_counts(dataset, valid_records),
            issues=issues,
        )

    def validate_all(self) -> EnvironmentalValidationSummary:
        reports = [self.validate(dataset) for dataset in EnvironmentalDataset]
        return EnvironmentalValidationSummary(
            generatedAt=self.as_of,
            allUsable=all(report.usable for report in reports),
            reports=reports,
        )

    @staticmethod
    def _failure_status(
        dataset: EnvironmentalDataset, *, malformed: bool
    ) -> DataStatus:
        if dataset is EnvironmentalDataset.RAINFALL:
            return DataStatus.DATA_UNAVAILABLE
        return (
            DataStatus.PROVIDER_UNAVAILABLE
            if malformed
            else DataStatus.DATA_UNAVAILABLE
        )
