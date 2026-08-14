from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..provenance.models import DataStatus, ValueProvenance
from .location import NormalizedLocation


class EnvironmentalResolution(str, Enum):
    PROPERTY_MEASURED = "PROPERTY_MEASURED"
    NEARBY_OBSERVATION = "NEARBY_OBSERVATION"
    GRIDDED_DATA = "GRIDDED_DATA"
    DISTRICT_LEVEL = "DISTRICT_LEVEL"
    REGIONAL_LAYER = "REGIONAL_LAYER"


class InfiltrationDataType(str, Enum):
    PROPERTY_MEASURED = "PROPERTY_MEASURED"
    REGIONAL_SOIL_PROXY = "REGIONAL_SOIL_PROXY"


class GroundwaterObservation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    station_id: str = Field(alias="stationId")
    station_name: str = Field(alias="stationName")
    station_type: str | None = Field(default=None, alias="stationType")
    aquifer_nature: str | None = Field(default=None, alias="aquiferNature")
    depth_below_ground_level_m: float = Field(
        ge=0, alias="depthBelowGroundLevelM"
    )
    depth_unit: str = Field(alias="depthUnit")
    observation_date: date = Field(alias="observationDate")
    season: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    district: str
    state: str
    distance_from_property_m: float | None = Field(
        default=None, ge=0, alias="distanceFromPropertyM"
    )
    spatial_resolution: EnvironmentalResolution = Field(alias="spatialResolution")
    provenance: ValueProvenance


class GroundwaterLookup(BaseModel):
    status: DataStatus
    observation: GroundwaterObservation | None = None
    message: str
    record_count: int = Field(default=0, alias="recordCount")


class SoilInformation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    record_id: str = Field(alias="recordId")
    soil_class: str | None = Field(default=None, alias="soilClass")
    soil_texture: str | None = Field(default=None, alias="soilTexture")
    permeability_class: str | None = Field(default=None, alias="permeabilityClass")
    source_category: str | None = Field(default=None, alias="sourceCategory")
    source_code: str | None = Field(default=None, alias="sourceCode")
    dataset_name: str | None = Field(default=None, alias="datasetName")
    dataset_version: str | None = Field(default=None, alias="datasetVersion")
    source_organization: str | None = Field(default=None, alias="sourceOrganization")
    measured_infiltration_rate_mm_per_hr: float | None = Field(
        default=None, ge=0, alias="measuredInfiltrationRateMmPerHr"
    )
    infiltration_data_type: InfiltrationDataType = Field(alias="infiltrationDataType")
    spatial_resolution: EnvironmentalResolution = Field(alias="spatialResolution")
    field_test_recommended: bool = Field(alias="fieldTestRecommended")
    provenance: ValueProvenance
    bounding_box: tuple[float, float, float, float] | None = Field(
        default=None, alias="boundingBox"
    )
    geometry: dict[str, Any] | None = None


class SoilLookup(BaseModel):
    status: DataStatus
    information: SoilInformation | None = None
    message: str


class HydrogeologyInformation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    record_id: str = Field(alias="recordId")
    geology: str | None = None
    lithology: str | None = None
    geomorphology: str | None = None
    groundwater_prospect: str | None = Field(default=None, alias="groundwaterProspect")
    aquifer_type: str | None = Field(default=None, alias="aquiferType")
    aquifer_depth: str | None = Field(default=None, alias="aquiferDepth")
    aquifer_thickness: str | None = Field(default=None, alias="aquiferThickness")
    spatial_resolution: EnvironmentalResolution = Field(alias="spatialResolution")
    dataset_version: str = Field(alias="datasetVersion")
    provenance: ValueProvenance
    bounding_box: tuple[float, float, float, float] | None = Field(
        default=None, alias="boundingBox"
    )
    geometry: dict[str, Any] | None = None


class HydrogeologyLookup(BaseModel):
    status: DataStatus
    information: HydrogeologyInformation | None = None
    geology_status: DataStatus = Field(alias="geologyStatus")
    geomorphology_status: DataStatus = Field(alias="geomorphologyStatus")
    aquifer_status: DataStatus = Field(alias="aquiferStatus")
    groundwater_prospect_status: DataStatus = Field(alias="groundwaterProspectStatus")
    message: str


class AREnvironmentalProfile(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    location: NormalizedLocation
    groundwater: GroundwaterLookup
    soil: SoilLookup
    hydrogeology: HydrogeologyLookup
    assembled_at: datetime = Field(alias="assembledAt")
