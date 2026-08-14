"use client";

import Link from "next/link";
import { useEffect } from "react";
import { InfoNotice } from "@/components/InfoNotice";
import { ResultSection, StatusBadge } from "@/components/ResultUI";
import { displayLabel } from "@/lib/types";
import type { AssessmentResult } from "@/lib/types";
import { SERVER_SNAPSHOT, useSessionValue } from "@/lib/session";

const number = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const value = (amount: number | null, suffix = "") =>
  amount === null ? "Unavailable" : `${number.format(amount)}${suffix}`;

function homeownerArStatus(status: string, hasStructure: boolean) {
  if (status === "ELIGIBLE" || status === "SUITABLE") return "Suitable";
  if (status === "CONDITIONALLY_ELIGIBLE" || status === "CONDITIONALLY_SUITABLE") return "Conditional";
  if (status === "UNSUITABLE" || status === "NOT_RECOMMENDED") return "Unsuitable";
  return hasStructure ? "Conditional" : "Not assessable";
}

function homeownerRtrwhStatus(status: string, potential: number | null) {
  if (status === "SUITABLE") return "Suitable";
  return potential !== null ? "Assessment available" : "Not assessable";
}

function Dimensions({ dimensions }: { dimensions: Record<string, unknown> | null }) {
  if (!dimensions) return null;

  const groups = [
    { label: "Trench", keys: ["trenchLengthM", "trenchWidthM", "trenchDepthM"] },
    { label: "Surface chamber", keys: ["chamberLengthM", "chamberWidthM", "chamberDepthM"] },
  ];
  const group = groups.find(({ keys }) => keys.every((key) => typeof dimensions[key] === "number"));
  const options = Array.isArray(dimensions.wellOptions)
    ? dimensions.wellOptions as Array<{ diameterM: number; publishedCalculatedDepthM?: number; minimumDesignDepthM: number }>
    : [];

  return (
    <div className="dimension-list">
      {group && (
        <div>
          <span>{group.label}</span>
          <strong>{group.keys.map((key) => `${dimensions[key]} m`).join(" × ")}</strong>
        </div>
      )}
      {options.map((option) => (
        <div key={`${option.diameterM}-${option.minimumDesignDepthM}`}>
          <span>Recharge well</span>
          <strong>{option.diameterM} m diameter × {option.minimumDesignDepthM} m published minimum depth</strong>
        </div>
      ))}
    </div>
  );
}

function ResultMetric({ label, amount, unit }: { label: string; amount: number | null; unit: string }) {
  return (
    <div className={`result-metric ${amount === null ? "metric-unavailable" : ""}`}>
      <span>{label}</span>
      <strong>{value(amount)}</strong>
      {amount !== null && <small>{unit}</small>}
    </div>
  );
}

export default function ResultPage() {
  const storedResult = useSessionValue("rainassess-result");

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, []);

  if (storedResult === SERVER_SNAPSHOT) {
    return <main className="page-main"><div className="shell loading-state" role="status">Loading assessment summary…</div></main>;
  }

  let result: AssessmentResult | null = null;
  try {
    result = storedResult ? JSON.parse(storedResult) : null;
  } catch {
    result = null;
  }

  if (!result) {
    return (
      <main className="page-main">
        <div className="shell empty-state">
          <span className="empty-icon" aria-hidden="true">i</span>
          <h1>No assessment result found</h1>
          <p>Complete the property assessment to generate your preliminary rainwater and recharge summary.</p>
          <Link className="button button-primary" href="/assessment">Start Assessment <span aria-hidden="true">→</span></Link>
        </div>
      </main>
    );
  }

  const input = result.inputs;
  const ar = result.artificialRecharge;
  const environmental = ar.environmentalProfile;
  const hasStructure = Boolean(ar.recommendedStructure);
  const arStatus = homeownerArStatus(ar.feasibilityStatus, hasStructure);
  const rtrwhStatus = homeownerRtrwhStatus(result.rtrwhSuitability, result.rtrwh.potentialLitresPerYear);
  const waterQualityCriterion = ar.criteria.find(
    (criterion) => criterion.criterion === "water_quality_and_contamination_risk",
  );
  const location = result.derived.normalizedLocation?.canonicalName ?? input.location;
  const authorities = Array.from(new Set(result.sources.map((source) => source.authority)));

  return (
    <main className="page-main results-main">
      <div className="page-title-band result-title-band">
        <div className="shell result-title-layout">
          <div>
            <span className="breadcrumb">Home <b aria-hidden="true">/</b> Assessment Result</span>
            <h1>Assessment Result</h1>
            <p>Preliminary rainwater harvesting and artificial recharge assessment.</p>
          </div>
          <Link className="button button-light" href="/assessment">← Back to Inputs</Link>
        </div>
      </div>

      <div className="shell page-content result-content compact-results">
        <section className="result-location" aria-label="Assessment location">
          <span>Location</span>
          <strong>{location}</strong>
        </section>

        {result.isDemoData && (
          <InfoNotice title="Unvalidated ruleset in use" tone="warning">
            <p>Results use configured values that have not been validated as engineering data. They must not be used for construction.</p>
          </InfoNotice>
        )}

        <ResultSection title="Rooftop Rainwater Harvesting" eyebrow="Key results" className="essential-results">
          <div className="result-metrics-grid">
            <ResultMetric label="Annual Rainwater Harvest" amount={result.rtrwh.potentialLitresPerYear} unit="L/year" />
            <ResultMetric label="Recommended Tank Size" amount={result.rtrwh.recommendedSizeLitres} unit="litres" />
            <ResultMetric label="Water Available for Recharge" amount={ar.potentialRechargeLitresPerYear} unit="L/year" />
          </div>
        </ResultSection>

        <ResultSection title="Artificial Recharge" eyebrow="Preliminary recommendation" className="essential-results">
          {!hasStructure ? (
            <div className="ar-unavailable" role="status">
              <StatusBadge value={arStatus} />
              <h3>Detailed AR assessment is not yet available for this location.</h3>
              <p>Rainwater harvesting can still be assessed, but the groundwater, soil/infiltration, hydrogeological, or regional design evidence needed for a detailed recharge recommendation has not yet been validated here.</p>
            </div>
          ) : (
            <>
              <div className="ar-summary-grid">
                <div><span>AR Status</span><StatusBadge value={arStatus} /></div>
                <div><span>Suggested Structure</span><strong>{ar.recommendedStructure?.displayName}</strong></div>
                <div><span>Indicative Design</span><strong>{ar.dimensions ? "Available" : "Requires site verification"}</strong></div>
              </div>
              {ar.dimensions && (
                <div className="indicative-dimensions">
                  <h3>Indicative Dimensions</h3>
                  <Dimensions dimensions={ar.dimensions} />
                </div>
              )}
              {(ar.fieldVerificationRequired.length > 0 || ar.fieldTestsRecommended.length > 0) && (
                <p className="field-check-summary">
                  Field checks are required before construction.
                  {ar.recommendedStructure?.type.includes("WELL") && " Final recharge-well and aquifer intake depth must be confirmed on site."}
                </p>
              )}
            </>
          )}
        </ResultSection>

        <ResultSection title="Overall Assessment" eyebrow="At a glance" className="overall-section">
          <div className="simple-overall">
            <div><span aria-hidden="true">{result.rtrwh.potentialLitresPerYear !== null ? "✓" : "!"}</span><p>Rainwater Harvesting<strong>{rtrwhStatus}</strong></p></div>
            <div><span aria-hidden="true">{arStatus === "Suitable" ? "✓" : "!"}</span><p>Artificial Recharge<strong>{arStatus === "Not assessable" ? "Detailed assessment not available for this location" : arStatus}</strong></p></div>
          </div>
        </ResultSection>

        <div className="result-disclosures">
          <details className="calculation-details">
            <summary>How was this calculated?</summary>
            <div>
              <p><strong>Annual harvest:</strong> rainfall × roof area × runoff coefficient.</p>
              <div className="formula-row">
                <span>{value(result.derived.annualRainfallMm, " mm")}</span><b>×</b><span>{input.roofAreaM2} m²</span><b>×</b><span>{result.derived.runoffCoefficient ?? "Unavailable"}</span><b>=</b><strong>{value(result.rtrwh.potentialLitresPerYear, " L/year")}</strong>
              </div>
              <p><strong>Tank and recharge water:</strong> monthly rainfall, planned monthly use, and tank capacity are simulated over the normal year. Overflow is reported as water potentially available for recharge; it is not confirmed aquifer recharge.</p>
              <dl className="technical-list">
                <div><dt>Monthly use</dt><dd>{value(result.rtrwh.demandUsedLitresPerMonth, " L/month")}</dd></div>
                <div><dt>Modeled supply</dt><dd>{value(result.rtrwh.estimatedSupplyLitres, " L/year")}</dd></div>
                <div><dt>Modeled overflow</dt><dd>{value(result.rtrwh.estimatedOverflowLitres, " L/year")}</dd></div>
                <div><dt>Demand met</dt><dd>{value(result.rtrwh.demandMetPercent, "%")}</dd></div>
              </dl>
            </div>
          </details>

          <details className="calculation-details">
            <summary>Technical site evidence</summary>
            <div>
              <dl className="technical-list">
                <div><dt>Rainfall evidence</dt><dd>{value(result.derived.annualRainfallMm, " mm/year")} — {result.derived.rainfallSource ?? "source unavailable"}</dd></div>
                <div><dt>Runoff coefficient</dt><dd>{result.derived.runoffCoefficient ?? "Unavailable"}</dd></div>
                <div><dt>Feasibility status</dt><dd>{displayLabel(ar.feasibilityStatus)}</dd></div>
                <div><dt>Structure-selection status</dt><dd>{displayLabel(ar.structureSelectionStatus)}</dd></div>
                <div><dt>Sizing status</dt><dd>{displayLabel(ar.sizingStatus)}</dd></div>
                <div><dt>Harvest calculation method</dt><dd>{result.formula.methodId}</dd></div>
                <div><dt>Storage sizing method</dt><dd>{result.rtrwh.sizingMethodId}</dd></div>
                <div><dt>Recharge water-balance method</dt><dd>{ar.quantityMethodId}</dd></div>
                <div><dt>Structure sizing method</dt><dd>{ar.sizingMethodId}</dd></div>
                <div><dt>Water-quality verification</dt><dd>{waterQualityCriterion ? displayLabel(waterQualityCriterion.result) : "Not available"}</dd></div>
                {environmental && <>
                  <div><dt>Groundwater observation</dt><dd>{environmental.groundwater.observation ? `${environmental.groundwater.observation.depthBelowGroundLevelM} m bgl at ${environmental.groundwater.observation.stationName} (${displayLabel(environmental.groundwater.status)})` : displayLabel(environmental.groundwater.status)}</dd></div>
                  <div><dt>Regional soil / infiltration evidence</dt><dd>{environmental.soil.information?.soilTexture ?? environmental.soil.information?.soilClass ?? displayLabel(environmental.soil.status)}</dd></div>
                  <div><dt>Regional geology</dt><dd>{environmental.hydrogeology.information?.geology ?? displayLabel(environmental.hydrogeology.geologyStatus)}</dd></div>
                  <div><dt>Regional geomorphology</dt><dd>{environmental.hydrogeology.information?.geomorphology ?? displayLabel(environmental.hydrogeology.geomorphologyStatus)}</dd></div>
                  <div><dt>Regional aquifer / prospects</dt><dd>{environmental.hydrogeology.information?.aquiferType ?? environmental.hydrogeology.information?.groundwaterProspect ?? displayLabel(environmental.hydrogeology.aquiferStatus)}</dd></div>
                </>}
              </dl>
              {environmental?.groundwater.observation && <p>This is a nearby observation approximately {value(environmental.groundwater.observation.distanceFromPropertyM, " m")} from the property, not a measurement directly beneath it. Observation: {environmental.groundwater.observation.observationDate ?? environmental.groundwater.observation.observationPeriod ?? "date unavailable"}.</p>}
              {environmental?.soil.information && <p>Regional mapped soil is a proxy. Measured property infiltration is {environmental.soil.information.measuredInfiltrationRateMmPerHr == null ? "not available" : `${environmental.soil.information.measuredInfiltrationRateMmPerHr} mm/hour`}.</p>}
              {ar.criteria.length > 0 && <><h3>Feasibility conditions</h3><ul>{ar.criteria.map((criterion) => <li key={criterion.criterion}><strong>{displayLabel(criterion.criterion)}:</strong> {criterion.reason}</li>)}</ul></>}
              {ar.selectionReasons.length > 0 && <><h3>Selection reasons</h3><ul>{ar.selectionReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></>}
              {ar.rejectedStructures.length > 0 && <><h3>Rejected alternatives</h3><ul>{ar.rejectedStructures.map((item) => <li key={`${item.structure}-${item.reason}`}><strong>{displayLabel(item.structure)}:</strong> {item.reason}</li>)}</ul></>}
              {ar.alternativeStructures.length > 0 && <><h3>Other conditional options</h3><ul>{ar.alternativeStructures.map((item) => <li key={item}>{displayLabel(item)}</li>)}</ul></>}
              {ar.filterMedia.length > 0 && <><h3>Filter and media requirements</h3><ul>{ar.filterMedia.map((item) => <li key={item}>{item}</li>)}</ul></>}
              {[...ar.fieldTestsRecommended, ...ar.fieldVerificationRequired].length > 0 && <><h3>Field verification required</h3><ul>{[...new Set([...ar.fieldTestsRecommended, ...ar.fieldVerificationRequired])].map((item) => <li key={item}>{item}</li>)}</ul></>}
              {ar.message && <p>{ar.message}</p>}
            </div>
          </details>

          {result.sources.length > 0 && (
            <details className="calculation-details">
              <summary>Sources: {authorities.join(" · ")}</summary>
              <div>
                <p>Sources support the methods and evidence shown; a listed source does not imply that unavailable property data was inferred.</p>
                <ul>{result.sources.map((source) => <li key={source.sourceId}><a href={source.sourceUrl} target="_blank" rel="noreferrer">{source.authority}: {source.documentTitle}</a>{source.section ? ` — ${source.section}` : ""}{source.page ? `, page ${source.page}` : ""}</li>)}</ul>
              </div>
            </details>
          )}
        </div>

        <InfoNotice title="Preliminary assessment" tone="warning">
          <p>Field infiltration, groundwater and water-quality verification may be required before construction. Follow applicable government guidance and obtain professional site assessment where indicated.</p>
        </InfoNotice>

        <div className="result-actions">
          <Link className="button button-primary" href="/">Return Home</Link>
        </div>
      </div>
    </main>
  );
}
