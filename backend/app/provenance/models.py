from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DataStatus(str, Enum):
    DATA_AVAILABLE = "DATA_AVAILABLE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    DATA_STALE = "DATA_STALE"
    UNSUPPORTED_LOCATION = "UNSUPPORTED_LOCATION"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    FIELD_MEASUREMENT_REQUIRED = "FIELD_MEASUREMENT_REQUIRED"


class DataQuality(str, Enum):
    MEASURED = "MEASURED"
    AUTHORITATIVE_DATASET = "AUTHORITATIVE_DATASET"
    DERIVED = "DERIVED"
    USER_PROVIDED = "USER_PROVIDED"
    ENGINEERING_DEFAULT = "ENGINEERING_DEFAULT"
    ASSUMED = "ASSUMED"


class SourceCitation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(alias="sourceId")
    authority: str
    document_title: str = Field(alias="documentTitle")
    document_version_or_year: str = Field(alias="documentVersionOrYear")
    section: str | None = None
    page: str | None = None
    source_url: str = Field(alias="sourceUrl")
    accessed_at: date = Field(alias="accessedAt")
    notes: str | None = None


class ValueProvenance(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    quality: DataQuality
    source_ids: list[str] = Field(default_factory=list, alias="sourceIds")
    source_record: str | None = Field(default=None, alias="sourceRecord")
    source_date_or_version: str | None = Field(default=None, alias="sourceDateOrVersion")
    spatial_resolution: str | None = Field(default=None, alias="spatialResolution")
    temporal_resolution: str | None = Field(default=None, alias="temporalResolution")
    retrieved_at: datetime | None = Field(default=None, alias="retrievedAt")
    notes: str | None = None


class PublishedRange(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    published_min: float | None = Field(default=None, alias="publishedMin")
    published_max: float | None = Field(default=None, alias="publishedMax")
    selected_value: float | None = Field(default=None, alias="selectedValue")
    selection_method: str | None = Field(default=None, alias="selectionMethod")
