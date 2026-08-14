from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from ..provenance.models import DataStatus


class EnvironmentalDataset(str, Enum):
    RAINFALL = "rainfall"
    GROUNDWATER = "groundwater"
    SOIL = "soil"
    HYDROGEOLOGY = "hydrogeology"


class CacheValidationStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    STALE = "STALE"
    EMPTY = "EMPTY"
    MISSING = "MISSING"
    MALFORMED = "MALFORMED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED_METADATA = "UNSUPPORTED_METADATA"


class EnvironmentalCoverage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    bounding_box: tuple[float, float, float, float] | None = Field(
        default=None, alias="boundingBox"
    )
    states: list[str] = Field(default_factory=list)
    districts: list[str] = Field(default_factory=list)
    spatial_resolutions: list[str] = Field(
        default_factory=list, alias="spatialResolutions"
    )


class EnvironmentalCacheReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    dataset: EnvironmentalDataset
    status: CacheValidationStatus
    provider_status: DataStatus = Field(alias="providerStatus")
    usable: bool
    record_count: int = Field(default=0, alias="recordCount")
    valid_record_count: int = Field(default=0, alias="validRecordCount")
    invalid_record_count: int = Field(default=0, alias="invalidRecordCount")
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    source_names: list[str] = Field(default_factory=list, alias="sourceNames")
    dataset_version: str | None = Field(default=None, alias="datasetVersion")
    imported_at: datetime | None = Field(default=None, alias="importedAt")
    observation_period: str | None = Field(default=None, alias="observationPeriod")
    latest_observation_date: date | None = Field(
        default=None, alias="latestObservationDate"
    )
    freshness_policy: str = Field(alias="freshnessPolicy")
    coverage: EnvironmentalCoverage | None = None
    component_counts: dict[str, int] = Field(
        default_factory=dict, alias="componentCounts"
    )
    issues: list[str] = Field(default_factory=list)


class EnvironmentalValidationSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    generated_at: datetime = Field(alias="generatedAt")
    all_usable: bool = Field(alias="allUsable")
    reports: list[EnvironmentalCacheReport]
