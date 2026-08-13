import { describe, expect, it } from "vitest";
import { displayLabel } from "./types";

describe("displayLabel", () => {
  it("formats known engineering enum values for homeowners", () => {
    expect(displayLabel("SANDY_LOAM")).toBe("Sandy Loam");
    expect(displayLabel("NOT_RECOMMENDED")).toBe("Not recommended");
  });

  it("gracefully displays unavailable values", () => {
    expect(displayLabel(null)).toBe("Unavailable");
  });
});
