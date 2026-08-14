from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class LocationResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    NOT_RESOLVED = "NOT_RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"


class NormalizedLocation(BaseModel):
    """Provider-neutral location passed to environmental data providers."""

    model_config = ConfigDict(populate_by_name=True)

    input: str
    canonical_name: str = Field(alias="canonicalName")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    district: str | None = None
    state: str | None = None
    country: str
    provider: str
    provider_place_id: str | None = Field(default=None, alias="providerPlaceId")
    confidence: str
    candidate_count: int | None = Field(default=None, ge=1, alias="candidateCount")


class LocationResolution(BaseModel):
    status: LocationResolutionStatus
    location: NormalizedLocation | None = None
    message: str
