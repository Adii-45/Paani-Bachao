from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..provenance.models import DataStatus, PublishedRange, ValueProvenance


class LocationQuery(BaseModel):
    location: str
    latitude: float | None = None
    longitude: float | None = None
    state: str | None = None
    district: str | None = None


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
    source_record: str = Field(alias="sourceRecord")
    dataset_version: str = Field(alias="datasetVersion")
    retrieved_at: datetime = Field(alias="retrievedAt")


class RainfallLookup(BaseModel):
    status: DataStatus
    record: RainfallRecord | None = None
    message: str


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
