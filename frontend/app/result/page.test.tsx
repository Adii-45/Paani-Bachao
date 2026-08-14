import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { AssessmentResult } from "@/lib/types";
import ResultPage from "./page";

const { sessionValue } = vi.hoisted(() => ({
  sessionValue: vi.fn<(key: string) => string | null>(),
}));

vi.mock("@/lib/session", () => ({
  SERVER_SNAPSHOT: "__SERVER_SNAPSHOT__",
  useSessionValue: sessionValue,
}));

// CGWB Manual (2007), §7.2.7.1, page 119 worked example.
const sourceBackedResult: AssessmentResult = {
  inputs: {
    location: "Published Example",
    roofAreaM2: 20,
    roofMaterial: "OTHER",
    soilType: "DONT_KNOW",
    groundwaterDepthM: 8,
    availableGroundAreaM2: 15,
  },
  derived: {
    locationStatus: "RESOLVED",
    normalizedLocation: {
      canonicalName: "Example District, Example State, India",
      latitude: 12.5,
      longitude: 77.5,
      district: "Example District",
      state: "Example State",
      provider: "test fixture",
      confidence: "fixture",
    },
    annualRainfallMm: 1000,
    rainfallSource: "CGWB published worked example",
    runoffCoefficient: 0.75,
    rainfallStatus: "DATA_AVAILABLE",
    rainfall: {
      message: "Published worked example.",
      referencePeriod: "CGWB worked example",
      spatialResolution: "worked example",
      sourceName: "Central Ground Water Board (CGWB)",
      sourceUrl: "https://cgwb.gov.in/example-rainfall.pdf",
    },
    runoffCoefficientStatus: "DATA_AVAILABLE",
    runoffCoefficientEvidence: { message: "Published worked-example coefficient." },
  },
  rtrwh: {
    potentialLitresPerYear: 15_000,
    recommendedSizeLitres: null,
    sizingMessage: "Storage capacity cannot be sized from annual harvesting potential alone.",
    calculationStatus: "DATA_AVAILABLE",
    sizingStatus: "INSUFFICIENT_DATA_FOR_SIZING",
    sizingMethodId: "CGWB_MANUAL_2007_STORAGE_DATA_REQUIREMENTS",
  },
  artificialRecharge: {
    potential: null,
    potentialRechargeLitresPerYear: null,
    recommendedStructure: null,
    dimensions: null,
    message: "Rechargeable water requires a documented allocation balance.",
    feasibilityStatus: "INSUFFICIENT_DATA",
    criteria: [
      {
        criterion: "hydrogeology_and_aquifer",
        result: "INSUFFICIENT_DATA",
        observedValue: null,
        requiredCondition: "Applicable hydrogeological evidence.",
        reason: "No applicable CGWB/NAQUIM feature is available.",
        sourceIds: ["CGWB_NAQUIM"],
      },
    ],
    quantityStatus: "INSUFFICIENT_DATA",
    structureSelectionStatus: "INSUFFICIENT_DATA_FOR_SELECTION",
    sizingStatus: "INSUFFICIENT_DATA_FOR_SIZING",
  },
  rtrwhSuitability: "SUITABILITY_NOT_DETERMINED",
  dataCompleteness: "INSUFFICIENT",
  assessmentStatus: "PRELIMINARY",
  ruleset: "SOURCE_BACKED",
  isDemoData: false,
  formula: {
    expression: "rainfall (mm/year) × roof area (m²) × runoff coefficient",
    roofAreaM2: 20,
    annualRainfallMm: 1000,
    runoffCoefficient: 0.75,
    methodId: "CGWB_MANUAL_2007_RTRWH_ANNUAL_VOLUME",
    grossRainfallVolumeLitres: 20_000,
    estimatedLossesLitres: 5_000,
    harvestableVolumeLitres: 15_000,
    sourceIds: ["CGWB_MANUAL_AR_2007"],
  },
  warnings: [],
  sources: [
    {
      sourceId: "CGWB_MANUAL_AR_2007",
      authority: "Central Ground Water Board (CGWB)",
      documentTitle: "Manual on Artificial Recharge of Ground Water",
      documentVersionOrYear: "2007",
      section: "7.2.7.1",
      page: "119",
      sourceUrl: "https://cgwb.gov.in/example.pdf",
    },
  ],
};

beforeEach(() => {
  sessionValue.mockReset();
  window.scrollTo = vi.fn();
});

describe("assessment results", () => {
  it("renders source-backed harvest details and honest unavailable decisions", () => {
    sessionValue.mockReturnValue(JSON.stringify(sourceBackedResult));
    render(<ResultPage />);

    expect(screen.getByRole("heading", { name: "Rainwater & Recharge Assessment" })).toBeInTheDocument();
    expect(screen.getAllByText("15,000").length).toBeGreaterThan(0);
    expect(screen.getByText(/Gross rainfall volume: 20,000 L\/year/)).toBeInTheDocument();
    expect(screen.getByText("Example District, Example State, India")).toBeInTheDocument();
    expect(screen.getByText("Reference period: CGWB worked example")).toBeInTheDocument();
    expect(screen.getByText("Resolution: worked example")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View rainfall source" })).toHaveAttribute(
      "href",
      "https://cgwb.gov.in/example-rainfall.pdf",
    );
    expect(screen.getAllByText("Insufficient data").length).toBeGreaterThan(0);
    expect(screen.getByText(/No applicable CGWB\/NAQUIM feature/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Manual on Artificial Recharge/ })).toHaveAttribute(
      "href",
      "https://cgwb.gov.in/example.pdf",
    );
    expect(screen.getByRole("link", { name: "← Back to Inputs" })).toHaveAttribute("href", "/assessment");
    expect(screen.queryByText("Recharge Trench")).not.toBeInTheDocument();
  });

  it("renders unavailable source data without substituting numeric results", () => {
    const unavailable: AssessmentResult = {
      ...sourceBackedResult,
      derived: {
        annualRainfallMm: null,
        rainfallSource: null,
        runoffCoefficient: null,
        rainfallStatus: "DATA_UNAVAILABLE",
        rainfall: {
          message: "Official rainfall data are unavailable.",
          referencePeriod: null,
          spatialResolution: null,
        },
      },
      rtrwh: {
        ...sourceBackedResult.rtrwh,
        potentialLitresPerYear: null,
        recommendedSizeLitres: null,
      },
      formula: {
        ...sourceBackedResult.formula,
        annualRainfallMm: null,
        runoffCoefficient: null,
        grossRainfallVolumeLitres: null,
        estimatedLossesLitres: null,
        harvestableVolumeLitres: null,
      },
    };
    sessionValue.mockReturnValue(JSON.stringify(unavailable));
    render(<ResultPage />);

    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(3);
    expect(screen.queryByText("15,000")).not.toBeInTheDocument();
    expect(screen.queryByText("6,000")).not.toBeInTheDocument();
  });

  it("offers the assessment route when no stored result exists", () => {
    sessionValue.mockReturnValue(null);
    render(<ResultPage />);

    expect(screen.getByRole("heading", { name: "No assessment result found" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Start Assessment/ })).toHaveAttribute(
      "href",
      "/assessment",
    );
  });

  it("handles invalid stored data without showing a raw parsing error", () => {
    sessionValue.mockReturnValue("not-json");
    render(<ResultPage />);

    expect(screen.getByRole("heading", { name: "No assessment result found" })).toBeInTheDocument();
    expect(screen.queryByText(/SyntaxError/)).not.toBeInTheDocument();
  });
});
