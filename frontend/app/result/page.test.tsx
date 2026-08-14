import { fireEvent, render, screen } from "@testing-library/react";
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
      input: "Published Example",
      canonicalName: "Example District, Example State, India",
      latitude: 12.5,
      longitude: 77.5,
      district: "Example District",
      state: "Example State",
      country: "India",
      provider: "test fixture",
      confidence: "fixture",
      message: "Deterministic fixture",
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
    recommendedSizeLitres: 5_000,
    sizingMessage: "Capacity uses the IRICEN monthly cumulative-surplus method.",
    calculationStatus: "DATA_AVAILABLE",
    sizingStatus: "SIZE_AVAILABLE",
    sizingMethodId: "IRICEN_2022_MONTHLY_CUMULATIVE_SURPLUS",
    sizingDesignPeriod: "July-June normal year",
    sizingRainfallResolution: "IMD district monthly normal, 1971-2020",
    demandUsedLitresPerMonth: 2_000,
    estimatedSupplyLitres: 20_000,
    estimatedOverflowLitres: 1_000,
    demandMetPercent: 83.33,
    depletionMonths: [5, 6],
    sizingAssumptions: ["Monthly demand is constant at the user-entered value."],
    sizingMissingInputs: [],
    sizingSourceIds: ["IRICEN_RWH_2022"],
    sizingRainfallReferencePeriod: "1971-2020",
    sizingRainfallSourceUrls: [],
    sizingRainfallSourceRecords: [],
    storagePeriods: [],
  },
  artificialRecharge: {
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
    reasons: ["No applicable CGWB/NAQUIM feature is available."],
    quantityStatus: "INSUFFICIENT_DATA",
    quantityMethodId: "IRICEN_STORAGE_OVERFLOW_AVAILABLE_FOR_AR",
    annualHarvestLitres: null,
    annualDemandSuppliedLitres: null,
    annualOverflowLitres: null,
    catchmentLossesLitres: null,
    endingStorageLitres: null,
    quantityAssumptions: [],
    quantityMissingInputs: ["annual tank overflow"],
    conditionsPassed: [],
    conditionsFailed: [],
    conditionsRequiringVerification: [],
    missingData: ["No applicable CGWB/NAQUIM feature is available."],
    fieldTestsRecommended: [],
    structureSelectionStatus: "INSUFFICIENT_DATA_FOR_SELECTION",
    alternativeStructures: [],
    selectionReasons: [],
    rejectedStructures: [],
    structureMissingInputs: ["hydrogeology"],
    sizingStatus: "INSUFFICIENT_DATA_FOR_SIZING",
    sizingMethodId: "NOT_APPLICABLE",
    requiredFootprintM2: null,
    filterMedia: [],
    sizingDesignInputs: {},
    sizingAssumptions: [],
    fieldVerificationRequired: [],
    sizingMissingInputs: ["selected structure"],
    sourceIds: ["CGWB_NAQUIM"],
    environmentalProfile: {
      assembledAt: "2026-08-13T00:00:00Z",
      location: {
        canonicalName: "Example District, Example State, India",
        latitude: 12.5,
        longitude: 77.5,
        district: "Example District",
        state: "Example State",
      },
      groundwater: {
        status: "DATA_STALE",
        message: "Nearby CGWB observation; not a property measurement.",
        recordCount: 1,
        observation: {
          stationId: "W125200077350001",
          stationName: "Jayanagar",
          depthBelowGroundLevelM: 3,
          depthUnit: "m bgl",
          observationDate: "2022-11-05",
          season: "NOVEMBER_MONITORING",
          distanceFromPropertyM: 11407.7,
          spatialResolution: "NEARBY_OBSERVATION",
        },
      },
      soil: {
        status: "FIELD_MEASUREMENT_REQUIRED",
        message: "A field infiltration/percolation test is required.",
        information: null,
      },
      hydrogeology: {
        status: "DATA_UNAVAILABLE",
        geologyStatus: "DATA_UNAVAILABLE",
        geomorphologyStatus: "DATA_UNAVAILABLE",
        aquiferStatus: "DATA_UNAVAILABLE",
        groundwaterProspectStatus: "DATA_UNAVAILABLE",
        message: "No reviewed hydrogeology feature is available.",
        information: null,
      },
    },
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
    assumptions: ["Published deterministic fixture."],
  },
  environmentalData: {
    locationStatus: "RESOLVED",
    rainfall: { status: "DATA_AVAILABLE", evidenceAvailable: true, message: "Available", sourceIds: ["CGWB_MANUAL_AR_2007"], componentStatuses: {} },
    groundwater: { status: "DATA_STALE", evidenceAvailable: true, message: "Stale nearby observation", sourceIds: ["CGWB_NAQUIM"], componentStatuses: {} },
    soil: { status: "FIELD_MEASUREMENT_REQUIRED", evidenceAvailable: false, message: "Field test required", sourceIds: [], componentStatuses: {} },
    hydrogeology: { status: "DATA_UNAVAILABLE", evidenceAvailable: false, message: "Unavailable", sourceIds: [], componentStatuses: {} },
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
  it("keeps RTRWH visible and shows one clear message when detailed AR is unavailable", () => {
    sessionValue.mockReturnValue(JSON.stringify(sourceBackedResult));
    render(<ResultPage />);

    expect(screen.getByRole("heading", { name: "Assessment Result" })).toBeInTheDocument();
    expect(screen.getByText("Annual Rainwater Harvest")).toBeInTheDocument();
    expect(screen.getByText("15,000")).toBeInTheDocument();
    expect(screen.getByText("Recommended Tank Size")).toBeInTheDocument();
    expect(screen.getByText("5,000")).toBeInTheDocument();
    expect(screen.getByText("Example District, Example State, India")).toBeInTheDocument();
    expect(screen.getByText("Detailed AR assessment is not yet available for this location.")).toBeInTheDocument();
    expect(screen.getAllByText("Not assessable")).toHaveLength(1);
    expect(screen.queryByText("Structure option")).not.toBeInTheDocument();
    expect(screen.queryByText("Published indicative dimensions")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Environmental Evidence" })).not.toBeInTheDocument();
    expect(screen.getByText("Technical site evidence").closest("details")).not.toHaveAttribute("open");
    expect(screen.getByRole("link", { name: "← Back to Inputs" })).toHaveAttribute("href", "/assessment");
  });

  it("renders unavailable source data without substituting numeric results", () => {
    const unavailable: AssessmentResult = {
      ...sourceBackedResult,
      derived: {
        ...sourceBackedResult.derived,
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

    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.queryByText("15,000")).not.toBeInTheDocument();
    expect(screen.queryByText("6,000")).not.toBeInTheDocument();
  });

  it("renders a compact supported AR result and keeps engineering evidence expandable", () => {
    const rechargeResult: AssessmentResult = {
      ...sourceBackedResult,
      inputs: {
        ...sourceBackedResult.inputs,
        buildingHasBasement: false,
        waterQualityStatus: "VERIFIED_ACCEPTABLE",
        waterQualityEvidence: "Qualified laboratory report fixture",
      },
      artificialRecharge: {
        ...sourceBackedResult.artificialRecharge,
        potentialRechargeLitresPerYear: 1_000,
        annualDemandSuppliedLitres: 10_000,
        annualOverflowLitres: 1_000,
        endingStorageLitres: 4_000,
        quantityMethodId: "IRICEN_STORAGE_OVERFLOW_AVAILABLE_FOR_AR",
        feasibilityStatus: "ELIGIBLE",
        structureSelectionStatus: "RECOMMENDED",
        sizingStatus: "INDICATIVE_DESIGN_AVAILABLE",
        recommendedStructure: { type: "RECHARGE_TRENCH", displayName: "Recharge Trench" },
        dimensions: { trenchLengthM: 1.2, trenchWidthM: 1.2, trenchDepthM: 1.4 },
        selectionReasons: ["Reviewed formation is alluvial."],
        rejectedStructures: [
          { structure: "TRENCH_WITH_RECHARGE_WELL", reason: "Depth condition not met.", sourceIds: ["CGWB_DELHI_STANDARD_DESIGNS"] },
        ],
        filterMedia: ["0.4 m bottom layer of boulders"],
        fieldVerificationRequired: ["Complete a property-level infiltration test."],
      },
    };
    sessionValue.mockReturnValue(JSON.stringify(rechargeResult));
    render(<ResultPage />);

    expect(screen.getByText("Water Available for Recharge")).toBeInTheDocument();
    expect(screen.getByText("1,000")).toBeInTheDocument();
    expect(screen.getByText("AR Status")).toBeInTheDocument();
    expect(screen.getAllByText("Suitable").length).toBeGreaterThan(0);
    expect(screen.getByText("Recharge Trench")).toBeInTheDocument();
    expect(screen.getByText("1.2 m × 1.2 m × 1.4 m")).toBeInTheDocument();
    expect(screen.getByText(/Field checks are required before construction/)).toBeInTheDocument();
    const details = screen.getByText("Technical site evidence").closest("details");
    expect(details).not.toHaveAttribute("open");
    fireEvent.click(screen.getByText("Technical site evidence"));
    expect(details).toHaveAttribute("open");
    expect(screen.getByText("Reviewed formation is alluvial.")).toBeInTheDocument();
    expect(screen.getByText("Depth condition not met.")).toBeInTheDocument();
    expect(screen.getByText(/Complete a property-level infiltration test/)).toBeInTheDocument();
  });

  it("renders conditional recharge-well options without inventing intake depth", () => {
    const wellResult: AssessmentResult = {
      ...sourceBackedResult,
      artificialRecharge: {
        ...sourceBackedResult.artificialRecharge,
        feasibilityStatus: "CONDITIONALLY_ELIGIBLE",
        recommendedStructure: { type: "RECHARGE_WELL", displayName: "Recharge Well" },
        dimensions: {
          designStorageVolumeLitres: 2100,
          wellOptions: [{ diameterM: 0.91, minimumDesignDepthM: 3.35 }],
          finalAquiferIntakeDepthM: null,
        },
        alternativeStructures: ["RECHARGE_PIT"],
        structureSelectionStatus: "CONDITIONAL_RECOMMENDATION",
        sizingStatus: "PARTIAL_INDICATIVE_DESIGN",
        fieldVerificationRequired: ["Confirm a suitable aquifer intake zone before finalizing well depth."],
      },
    };
    sessionValue.mockReturnValue(JSON.stringify(wellResult));
    render(<ResultPage />);

    expect(screen.getByText("Recharge Well")).toBeInTheDocument();
    expect(screen.getByText("0.91 m diameter × 3.35 m published minimum depth")).toBeInTheDocument();
    expect(screen.getAllByText("Conditional").length).toBeGreaterThan(0);
    expect(screen.queryByText("Partial indicative design")).not.toBeVisible();
    fireEvent.click(screen.getByText("Technical site evidence"));
    expect(screen.getByText("Other conditional options")).toBeInTheDocument();
    expect(screen.getByText("Recharge pit")).toBeInTheDocument();
    expect(screen.getByText(/Confirm a suitable aquifer intake zone/)).toBeInTheDocument();
    expect(screen.getByText(/Final recharge-well and aquifer intake depth must be confirmed on site/)).toBeInTheDocument();
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
