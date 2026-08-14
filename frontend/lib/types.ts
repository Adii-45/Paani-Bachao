export type AssessmentInput = {
  location: string;
  roofAreaM2: number;
  roofMaterial: string;
  soilType: string;
  groundwaterDepthM: number;
  availableGroundAreaM2: number;
  monthlyRainwaterDemandLitres?: number;
  buildingHasBasement?: boolean;
  waterQualityStatus?: "NOT_VERIFIED" | "VERIFIED_ACCEPTABLE" | "UNSUITABLE";
  waterQualityEvidence?: string;
};

export type AssessmentResult = {
  inputs: AssessmentInput;
  derived: {
    locationStatus?: string;
    normalizedLocation?: {
      canonicalName: string;
      latitude: number;
      longitude: number;
      locality?: string | null;
      district: string | null;
      state: string | null;
      postalCode?: string | null;
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
    sizingDesignPeriod?: string;
    sizingRainfallResolution?: string | null;
    sizingRainfallReferencePeriod?: string | null;
    demandUsedLitresPerMonth?: number | null;
    estimatedSupplyLitres?: number | null;
    estimatedOverflowLitres?: number | null;
    demandMetPercent?: number | null;
    depletionMonths?: number[];
    sizingAssumptions?: string[];
    storagePeriods?: Array<{
      month: number;
      rainfallMm: number;
      inflowLitres: number;
      demandLitres: number;
      cumulativeSurplusLitres: number;
      suppliedLitres: number;
      unmetDemandLitres: number;
      overflowLitres: number;
      storageEndLitres: number;
    }>;
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
    quantityMethodId?: string;
    annualHarvestLitres?: number | null;
    annualDemandSuppliedLitres?: number | null;
    annualOverflowLitres?: number | null;
    catchmentLossesLitres?: number | null;
    endingStorageLitres?: number | null;
    quantityAssumptions?: string[];
    conditionsPassed?: string[];
    conditionsFailed?: string[];
    conditionsRequiringVerification?: string[];
    missingData?: string[];
    fieldTestsRecommended?: string[];
    structureSelectionStatus?: string;
    alternativeStructures?: string[];
    selectionReasons?: string[];
    rejectedStructures?: Array<{
      structure: string;
      reason: string;
      sourceIds: string[];
    }>;
    structureMissingInputs?: string[];
    sizingStatus?: string;
    sizingMethodId?: string;
    requiredFootprintM2?: number | null;
    filterMedia?: string[];
    sizingDesignInputs?: Record<string, string | number>;
    sizingAssumptions?: string[];
    fieldVerificationRequired?: string[];
    sizingMissingInputs?: string[];
    environmentalProfile?: {
      assembledAt: string;
      location: {
        canonicalName: string;
        latitude: number;
        longitude: number;
        district: string | null;
        state: string | null;
      };
      groundwater: {
        status: string;
        message: string;
        recordCount: number;
        observation: {
          stationId: string;
          stationName: string;
          depthBelowGroundLevelM: number;
          depthUnit: string;
          observationDate: string;
          season: string;
          distanceFromPropertyM: number | null;
          spatialResolution: string;
        } | null;
      };
      soil: {
        status: string;
        message: string;
        information: {
          soilClass: string | null;
          soilTexture: string | null;
          measuredInfiltrationRateMmPerHr: number | null;
          infiltrationDataType: string;
          fieldTestRecommended: boolean;
        } | null;
      };
      hydrogeology: {
        status: string;
        geologyStatus: string;
        geomorphologyStatus: string;
        aquiferStatus: string;
        groundwaterProspectStatus: string;
        message: string;
        information: {
          geology: string | null;
          lithology: string | null;
          geomorphology: string | null;
          groundwaterProspect: string | null;
          aquiferType: string | null;
        } | null;
      };
    } | null;
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
  environmentalData?: {
    locationStatus: string;
    rainfall: EnvironmentalProviderEvidence;
    groundwater: EnvironmentalProviderEvidence;
    soil: EnvironmentalProviderEvidence;
    hydrogeology: EnvironmentalProviderEvidence;
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

type EnvironmentalProviderEvidence = {
  status: string;
  evidenceAvailable: boolean;
  message: string;
  sourceIds: string[];
  componentStatuses: Record<string, string>;
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
