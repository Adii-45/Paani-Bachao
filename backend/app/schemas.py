from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .domain.environment import RainfallErrorCode
from .domain.ar_environment import AREnvironmentalProfile
from .domain.location import LocationResolutionStatus
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


class WaterQualityReviewStatus(str, Enum):
    NOT_VERIFIED = "NOT_VERIFIED"
    VERIFIED_ACCEPTABLE = "VERIFIED_ACCEPTABLE"
    UNSUITABLE = "UNSUITABLE"


class AssessmentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    location: str = Field(min_length=1, max_length=120)
    roofAreaM2: float = Field(gt=0, le=100_000)
    roofMaterial: RoofMaterial
    soilType: SoilType
    groundwaterDepthM: float = Field(ge=0, le=1_000)
    availableGroundAreaM2: float = Field(ge=0, le=100_000)
    monthlyRainwaterDemandLitres: float | None = Field(default=None, gt=0, le=10_000_000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    state: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    groundwaterObservationDate: date | None = None
    groundwaterObservationSeason: str | None = Field(default=None, max_length=80)
    groundwaterObservationMethod: str | None = Field(default=None, max_length=160)
    groundwaterSource: str | None = Field(default=None, max_length=160)
    buildingHasBasement: bool | None = None
    waterQualityStatus: WaterQualityReviewStatus = WaterQualityReviewStatus.NOT_VERIFIED
    waterQualityEvidence: str | None = Field(default=None, max_length=300)

    @field_validator("location")
    @classmethod
    def location_must_contain_text(cls, value: str) -> str:
        if not any(character.isalnum() for character in value):
            raise ValueError("Location must contain letters or numbers.")
        return value

    @model_validator(mode="after")
    def reviewed_water_quality_requires_evidence(self) -> "AssessmentRequest":
        if (
            self.waterQualityStatus is not WaterQualityReviewStatus.NOT_VERIFIED
            and not self.waterQualityEvidence
        ):
            raise ValueError(
                "A laboratory report, qualified review or source reference is required "
                "for a water-quality conclusion."
            )
        return self


class DerivedData(BaseModel):
    locationStatus: LocationResolutionStatus
    normalizedLocation: "NormalizedLocationEvidence | None"
    annualRainfallMm: float | None
    rainfallSource: str | None
    runoffCoefficient: float | None
    rainfallStatus: DataStatus
    rainfall: "RainfallEvidence"
    runoffCoefficientStatus: DataStatus
    runoffCoefficientEvidence: "RunoffCoefficientEvidence"


class NormalizedLocationEvidence(BaseModel):
    input: str
    canonicalName: str
    latitude: float
    longitude: float
    district: str | None
    state: str | None
    country: str
    provider: str
    providerPlaceId: str | None
    confidence: str
    candidateCount: int | None
    message: str


class RainfallEvidence(BaseModel):
    status: DataStatus
    value: float | None
    unit: str = "mm/year"
    statisticType: str | None = None
    referencePeriod: str | None = None
    spatialResolution: str | None = None
    sourceRecord: str | None = None
    datasetVersion: str | None = None
    sourceName: str | None = None
    sourceUrl: str | None = None
    provenance: ValueProvenance | None = None
    message: str
    errorCode: RainfallErrorCode | None = None


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
    sizingDesignPeriod: str
    sizingRainfallResolution: str | None
    sizingRainfallReferencePeriod: str | None
    sizingRainfallSourceUrls: list[str]
    sizingRainfallSourceRecords: list[str]
    demandUsedLitresPerMonth: float | None
    estimatedSupplyLitres: float | None
    estimatedOverflowLitres: float | None
    demandMetPercent: float | None
    depletionMonths: list[int]
    sizingAssumptions: list[str]
    storagePeriods: list["StoragePeriodResponse"]


class StoragePeriodResponse(BaseModel):
    month: int = Field(ge=1, le=12)
    rainfallMm: float
    inflowLitres: float
    demandLitres: float
    cumulativeSurplusLitres: float
    suppliedLitres: float
    unmetDemandLitres: float
    overflowLitres: float
    storageEndLitres: float


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
    quantityMethodId: str
    annualHarvestLitres: float | None
    annualDemandSuppliedLitres: float | None
    annualOverflowLitres: float | None
    catchmentLossesLitres: float | None
    endingStorageLitres: float | None
    quantityAssumptions: list[str]
    quantityMissingInputs: list[str]
    conditionsPassed: list[str]
    conditionsFailed: list[str]
    conditionsRequiringVerification: list[str]
    missingData: list[str]
    fieldTestsRecommended: list[str]
    structureSelectionStatus: str
    alternativeStructures: list[str]
    selectionReasons: list[str]
    rejectedStructures: list["RejectedStructureResponse"]
    structureMissingInputs: list[str]
    sizingStatus: str
    sizingMethodId: str
    requiredFootprintM2: float | None
    filterMedia: list[str]
    sizingDesignInputs: dict[str, Any]
    sizingAssumptions: list[str]
    fieldVerificationRequired: list[str]
    sizingMissingInputs: list[str]
    sourceIds: list[str]
    environmentalProfile: AREnvironmentalProfile | None = None


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
