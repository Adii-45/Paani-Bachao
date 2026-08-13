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

const completeResult: AssessmentResult = {
  inputs: {
    location: "Bengaluru",
    roofAreaM2: 120,
    roofMaterial: "RCC",
    soilType: "SANDY_LOAM",
    groundwaterDepthM: 8,
    availableGroundAreaM2: 15,
  },
  derived: {
    annualRainfallMm: 970,
    rainfallSource: "Configured test dataset",
    runoffCoefficient: 0.8,
  },
  rtrwh: {
    potentialLitresPerYear: 93_120,
    recommendedSizeLitres: 6_000,
    sizingMessage: null,
  },
  artificialRecharge: {
    potential: "HIGH",
    potentialRechargeLitresPerYear: 60_528,
    recommendedStructure: { type: "RECHARGE_TRENCH", displayName: "Recharge Trench" },
    dimensions: { lengthM: 3, widthM: 1, depthM: 1.5 },
    message: null,
  },
  rtrwhSuitability: "SUITABLE",
  dataCompleteness: "GOOD",
  assessmentStatus: "PRELIMINARY",
  ruleset: "DEMO",
  isDemoData: true,
  formula: {
    expression: "roof area (m²) × rainfall (mm/year) × runoff coefficient",
    roofAreaM2: 120,
    annualRainfallMm: 970,
    runoffCoefficient: 0.8,
  },
  warnings: ["DEMO / DEVELOPMENT VALUE — NOT VALIDATED"],
};

beforeEach(() => {
  sessionValue.mockReset();
  window.scrollTo = vi.fn();
});

describe("assessment results", () => {
  it("renders actual harvesting, sizing, recharge, structure, and formula values", () => {
    sessionValue.mockReturnValue(JSON.stringify(completeResult));
    render(<ResultPage />);

    expect(screen.getByRole("heading", { name: "Rainwater & Recharge Assessment" })).toBeInTheDocument();
    expect(screen.getByText("93,120")).toBeInTheDocument();
    expect(screen.getByText("6,000")).toBeInTheDocument();
    expect(screen.getByText("60,528 L/year")).toBeInTheDocument();
    expect(screen.getAllByText("High")).toHaveLength(2);
    expect(screen.getByText("Recharge Trench")).toBeInTheDocument();
    expect(screen.getByText("3 m × 1 m × 1.5 m")).toBeInTheDocument();
    expect(screen.getAllByText(/120 m²/)).toHaveLength(3);
    expect(screen.getByText(/Configured test dataset/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Back to Inputs" })).toHaveAttribute("href", "/assessment");
  });

  it("clearly renders unavailable engineering recommendations without substituting values", () => {
    const unavailable: AssessmentResult = {
      ...completeResult,
      derived: { annualRainfallMm: null, rainfallSource: null, runoffCoefficient: null },
      rtrwh: {
        potentialLitresPerYear: null,
        recommendedSizeLitres: null,
        sizingMessage: "Assessment unavailable. Engineering sizing rule not configured yet.",
      },
      artificialRecharge: {
        potential: null,
        potentialRechargeLitresPerYear: null,
        recommendedStructure: null,
        dimensions: null,
        message: "Assessment unavailable for this combination. Engineering rule not configured yet.",
      },
      rtrwhSuitability: "NOT ASSESSED",
      dataCompleteness: "INSUFFICIENT",
      ruleset: "PRODUCTION",
      isDemoData: false,
    };
    sessionValue.mockReturnValue(JSON.stringify(unavailable));
    render(<ResultPage />);

    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(3);
    expect(screen.getByText("Assessment unavailable. Engineering sizing rule not configured yet.")).toBeInTheDocument();
    expect(screen.getAllByText(/Engineering rule not configured yet/).length).toBeGreaterThan(0);
    expect(screen.queryByText("Recharge Trench")).not.toBeInTheDocument();
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
