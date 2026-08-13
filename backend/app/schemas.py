from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .provenance.models import DataStatus, PublishedRange, SourceCitation, ValueProvenance


class RoofMaterial(str, Enum):
    RCC = "RCC"
    TILES = "TILES"
    METAL = "METAL"
    OTHER = "OTHER"
    DONT_KNOW = "DONT_KNOW"


class SoilType(str, Enum):
    SANDY = "SANDY"
    SANDY_LOAM = "SANDY_LOAM"
    LOAM = "LOAM"
    CLAYEY = "CLAYEY"
    ROCKY = "ROCKY"
    DONT_KNOW = "DONT_KNOW"


class AssessmentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    location: str = Field(min_length=1, max_length=120)
    roofAreaM2: float = Field(gt=0, le=100_000)
    roofMaterial: RoofMaterial
    soilType: SoilType
    groundwaterDepthM: float = Field(ge=0, le=1_000)
    availableGroundAreaM2: float = Field(ge=0, le=100_000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    state: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    groundwaterObservationDate: date | None = None
    groundwaterObservationSeason: str | None = Field(default=None, max_length=80)
    groundwaterObservationMethod: str | None = Field(default=None, max_length=160)
    groundwaterSource: str | None = Field(default=None, max_length=160)

    @field_validator("location")
    @classmethod
    def location_must_contain_text(cls, value: str) -> str:
        if not any(character.isalnum() for character in value):
            raise ValueError("Location must contain letters or numbers.")
        return value


class DerivedData(BaseModel):
    annualRainfallMm: float | None
    rainfallSource: str | None
    runoffCoefficient: float | None
    rainfallStatus: DataStatus
    rainfall: "RainfallEvidence"
    runoffCoefficientStatus: DataStatus
    runoffCoefficientEvidence: "RunoffCoefficientEvidence"


class RainfallEvidence(BaseModel):
    status: DataStatus
    value: float | None
    unit: str = "mm/year"
    statisticType: str | None = None
    referencePeriod: str | None = None
    spatialResolution: str | None = None
    sourceRecord: str | None = None
    datasetVersion: str | None = None
    provenance: ValueProvenance | None = None
    message: str


class RunoffCoefficientEvidence(BaseModel):
    status: DataStatus
    valueRange: PublishedRange | None = None
    condition: str | None = None
    provenance: ValueProvenance | None = None
    message: str


class RtrwhResult(BaseModel):
    potentialLitresPerYear: float | None
    recommendedSizeLitres: float | None
    sizingMessage: str | None = None
    calculationStatus: DataStatus
    sizingStatus: str
    sizingMethodId: str
    sizingMissingInputs: list[str]
    sizingSourceIds: list[str]


class StructureRecommendation(BaseModel):
    type: str
    displayName: str


class ArtificialRechargeResult(BaseModel):
    potential: str | None
    potentialRechargeLitresPerYear: float | None
    recommendedStructure: StructureRecommendation | None
    dimensions: dict[str, Any] | None
    message: str | None = None
    feasibilityStatus: str
    criteria: list["FeasibilityCriterionResponse"]
    reasons: list[str]
    quantityStatus: str
    quantityMissingInputs: list[str]
    structureSelectionStatus: str
    alternativeStructures: list[str]
    selectionReasons: list[str]
    rejectedStructures: list["RejectedStructureResponse"]
    structureMissingInputs: list[str]
    sizingStatus: str
    sizingMissingInputs: list[str]
    sourceIds: list[str]


class FeasibilityCriterionResponse(BaseModel):
    criterion: str
    result: str
    observedValue: str | float | None
    requiredCondition: str
    reason: str
    sourceIds: list[str]


class RejectedStructureResponse(BaseModel):
    structure: str
    reason: str
    sourceIds: list[str]


class FormulaDetails(BaseModel):
    expression: str
    roofAreaM2: float
    annualRainfallMm: float | None
    runoffCoefficient: float | None
    methodId: str
    grossRainfallVolumeLitres: float | None
    estimatedLossesLitres: float | None
    harvestableVolumeLitres: float | None
    sourceIds: list[str]
    assumptions: list[str]


class AssessmentResponse(BaseModel):
    inputs: AssessmentRequest
    derived: DerivedData
    rtrwh: RtrwhResult
    artificialRecharge: ArtificialRechargeResult
    rtrwhSuitability: str
    dataCompleteness: str
    assessmentStatus: str = "PRELIMINARY"
    ruleset: str
    isDemoData: bool
    formula: FormulaDetails
    warnings: list[str]
    sources: list[SourceCitation]
