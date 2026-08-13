from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class RtrwhResult(BaseModel):
    potentialLitresPerYear: float | None
    recommendedSizeLitres: float | None
    sizingMessage: str | None = None


class StructureRecommendation(BaseModel):
    type: str
    displayName: str


class ArtificialRechargeResult(BaseModel):
    potential: str | None
    potentialRechargeLitresPerYear: float | None
    recommendedStructure: StructureRecommendation | None
    dimensions: dict[str, Any] | None
    message: str | None = None


class FormulaDetails(BaseModel):
    expression: str
    roofAreaM2: float
    annualRainfallMm: float | None
    runoffCoefficient: float | None


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
