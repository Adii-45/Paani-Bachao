export type AssessmentInput = {
  location: string;
  roofAreaM2: number;
  roofMaterial: string;
  soilType: string;
  groundwaterDepthM: number;
  availableGroundAreaM2: number;
};

export type AssessmentResult = {
  inputs: AssessmentInput;
  derived: {
    locationStatus?: string;
    normalizedLocation?: {
      canonicalName: string;
      latitude: number;
      longitude: number;
      district: string | null;
      state: string | null;
      provider: string;
      confidence: string;
    } | null;
    annualRainfallMm: number | null;
    rainfallSource: string | null;
    runoffCoefficient: number | null;
    rainfallStatus?: string;
    rainfall?: {
      message: string;
      referencePeriod: string | null;
      spatialResolution: string | null;
      sourceName?: string | null;
      sourceUrl?: string | null;
      errorCode?: string | null;
    };
    runoffCoefficientStatus?: string;
    runoffCoefficientEvidence?: { message: string };
  };
  rtrwh: {
    potentialLitresPerYear: number | null;
    recommendedSizeLitres: number | null;
    sizingMessage: string | null;
    calculationStatus?: string;
    sizingStatus?: string;
    sizingMethodId?: string;
    sizingMissingInputs?: string[];
    sizingSourceIds?: string[];
  };
  artificialRecharge: {
    potential: string | null;
    potentialRechargeLitresPerYear: number | null;
    recommendedStructure: { type: string; displayName: string } | null;
    dimensions: Record<string, string | number> | null;
    message: string | null;
    feasibilityStatus?: string;
    criteria?: Array<{
      criterion: string;
      result: string;
      observedValue: string | number | null;
      requiredCondition: string;
      reason: string;
      sourceIds: string[];
    }>;
    reasons?: string[];
    quantityStatus?: string;
    structureSelectionStatus?: string;
    structureMissingInputs?: string[];
    sizingStatus?: string;
  };
  rtrwhSuitability: string;
  dataCompleteness: string;
  assessmentStatus: string;
  ruleset: string;
  isDemoData: boolean;
  formula: {
    expression: string;
    roofAreaM2: number;
    annualRainfallMm: number | null;
    runoffCoefficient: number | null;
    methodId?: string;
    grossRainfallVolumeLitres?: number | null;
    estimatedLossesLitres?: number | null;
    harvestableVolumeLitres?: number | null;
    sourceIds?: string[];
    assumptions?: string[];
  };
  warnings: string[];
  sources?: Array<{
    sourceId: string;
    authority: string;
    documentTitle: string;
    documentVersionOrYear: string;
    section: string | null;
    page: string | null;
    sourceUrl: string;
  }>;
};

export const labels: Record<string, string> = {
  RCC: "RCC / Concrete", TILES: "Tiles", METAL: "GI sheet (galvanized iron)", OTHER: "Other", DONT_KNOW: "Don't know",
  SANDY: "Sandy", SANDY_LOAM: "Sandy Loam", LOAM: "Loam", CLAYEY: "Clayey", ROCKY: "Rocky",
  NOT_RECOMMENDED: "Not recommended", NOT_ASSESSED: "Not assessed",
};

export function displayLabel(value: string | null): string {
  if (!value) return "Unavailable";
  return labels[value] ?? value.charAt(0) + value.slice(1).toLowerCase().replaceAll("_", " ");
}
