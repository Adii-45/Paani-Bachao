from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..provenance.models import DataStatus, PublishedRange, ValueProvenance


class LocationQuery(BaseModel):
    location: str
    latitude: float | None = None
    longitude: float | None = None
    state: str | None = None
    district: str | None = None


class RainfallErrorCode(str, Enum):
    RAINFALL_DATA_UNAVAILABLE = "RAINFALL_DATA_UNAVAILABLE"
    RAINFALL_LOCATION_AMBIGUOUS = "RAINFALL_LOCATION_AMBIGUOUS"
    LOCATION_NOT_RESOLVED = "LOCATION_NOT_RESOLVED"


class MonthlyRainfallNormal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    values_mm: tuple[float, ...] = Field(
        min_length=12, max_length=12, alias="valuesMm"
    )
    reference_period: str = Field(alias="referencePeriod")
    spatial_resolution: str = Field(alias="spatialResolution")
    source_id: str = Field(alias="sourceId")
    source_name: str = Field(alias="sourceName")
    source_urls: tuple[str, ...] = Field(
        min_length=12, max_length=12, alias="sourceUrls"
    )
    source_records: tuple[str, ...] = Field(
        min_length=12, max_length=12, alias="sourceRecords"
    )
    dataset_version: str = Field(alias="datasetVersion")
    retrieved_at: datetime = Field(alias="retrievedAt")

    @field_validator("values_mm")
    @classmethod
    def rainfall_values_must_be_non_negative(
        cls, values: tuple[float, ...]
    ) -> tuple[float, ...]:
        if any(value < 0 for value in values):
            raise ValueError("Monthly rainfall cannot be negative.")
        return values


class RainfallRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    record_id: str = Field(alias="recordId")
    location_name: str = Field(alias="locationName")
    state: str | None = None
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    rainfall_mm: float = Field(ge=0, alias="rainfallMm")
    statistic_type: str = Field(alias="statisticType")
    reference_period: str = Field(alias="referencePeriod")
    spatial_resolution: str = Field(alias="spatialResolution")
    source_id: str = Field(alias="sourceId")
    source_name: str = Field(alias="sourceName")
    source_url: str = Field(alias="sourceUrl")
    source_record: str = Field(alias="sourceRecord")
    dataset_version: str = Field(alias="datasetVersion")
    retrieved_at: datetime = Field(alias="retrievedAt")
    bounding_box: tuple[float, float, float, float] | None = Field(
        default=None, alias="boundingBox"
    )
    geometry: dict[str, Any] | None = None
    monthly_normal: MonthlyRainfallNormal | None = Field(
        default=None, alias="monthlyNormal"
    )


class RainfallLookup(BaseModel):
    status: DataStatus
    record: RainfallRecord | None = None
    message: str
    error_code: RainfallErrorCode | None = None


class RunoffCoefficientRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    roof_type: str = Field(alias="roofType")
    value_range: PublishedRange = Field(alias="valueRange")
    condition: str
    source_ids: list[str] = Field(alias="sourceIds")
    provenance: ValueProvenance


class RunoffCoefficientLookup(BaseModel):
    status: DataStatus
    record: RunoffCoefficientRecord | None = None
    message: str
