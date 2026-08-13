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
  derived: { annualRainfallMm: number | null; rainfallSource: string | null; runoffCoefficient: number | null };
  rtrwh: { potentialLitresPerYear: number | null; recommendedSizeLitres: number | null; sizingMessage: string | null };
  artificialRecharge: {
    potential: string | null;
    potentialRechargeLitresPerYear: number | null;
    recommendedStructure: { type: string; displayName: string } | null;
    dimensions: Record<string, string | number> | null;
    message: string | null;
  };
  rtrwhSuitability: string;
  dataCompleteness: string;
  assessmentStatus: string;
  ruleset: string;
  isDemoData: boolean;
  formula: { expression: string; roofAreaM2: number; annualRainfallMm: number | null; runoffCoefficient: number | null };
  warnings: string[];
};

export const labels: Record<string, string> = {
  RCC: "RCC / Concrete", TILES: "Tiles", METAL: "Metal sheet", OTHER: "Other", DONT_KNOW: "Don't know",
  SANDY: "Sandy", SANDY_LOAM: "Sandy Loam", LOAM: "Loam", CLAYEY: "Clayey", ROCKY: "Rocky",
  NOT_RECOMMENDED: "Not recommended", NOT_ASSESSED: "Not assessed",
};

export function displayLabel(value: string | null): string {
  if (!value) return "Unavailable";
  return labels[value] ?? value.charAt(0) + value.slice(1).toLowerCase().replaceAll("_", " ");
}
