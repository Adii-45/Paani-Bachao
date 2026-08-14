"use client";

import Link from "next/link";
import { useEffect } from "react";
import { InfoNotice } from "@/components/InfoNotice";
import { ResultSection, StatusBadge } from "@/components/ResultUI";
import { displayLabel } from "@/lib/types";
import type { AssessmentResult } from "@/lib/types";
import { SERVER_SNAPSHOT, useSessionValue } from "@/lib/session";

const number = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const value = (amount: number | null, suffix = "") => amount === null ? "Unavailable" : `${number.format(amount)}${suffix}`;

function Dimensions({ dimensions }: { dimensions: Record<string, unknown> | null }) {
  if (!dimensions) return <>Unavailable</>;
  const groups = [
    { label: "Trench", keys: ["trenchLengthM", "trenchWidthM", "trenchDepthM"] },
    { label: "Surface chamber", keys: ["chamberLengthM", "chamberWidthM", "chamberDepthM"] },
  ];
  const group = groups.find(({ keys }) => keys.every((key) => key in dimensions));
  if (group) return <>{group.label}: {group.keys.map((key) => `${dimensions[key]} m`).join(" × ")}</>;
  const options = Array.isArray(dimensions.wellOptions) ? dimensions.wellOptions as Array<{diameterM: number; minimumDesignDepthM: number}> : [];
  if (options.length) return <>{options.map((option) => `${option.diameterM} m diameter × ${option.minimumDesignDepthM} m published minimum geometric depth`).join("; ")}</>;
  return <>Partial dimensions available in the engineering details</>;
}

function MetricValue({ amount, unit }: { amount: number | null; unit: string }) {
  return (
    <div className={`official-metric ${amount === null ? "metric-unavailable" : ""}`}>
      <strong>{value(amount)}</strong>
      {amount !== null && <span>{unit}</span>}
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
  const arMessage = result.artificialRecharge.message;
  const rechargeStatus = result.artificialRecharge.feasibilityStatus;
  const environmental = result.artificialRecharge.environmentalProfile;
  const waterQualityCriterion = result.artificialRecharge.criteria.find(
    (criterion) => criterion.criterion === "water_quality_and_contamination_risk",
  );

  return (
    <main className="page-main results-main">
      <div className="page-title-band result-title-band">
        <div className="shell result-title-layout">
          <div>
            <span className="breadcrumb">Home <b aria-hidden="true">/</b> Assessment Result</span>
            <h1>Rainwater &amp; Recharge Assessment</h1>
            <p>Preliminary assessment summary for the property information provided.</p>
          </div>
          <Link className="button button-light" href="/assessment">← Back to Inputs</Link>
        </div>
      </div>

      <div className="shell page-content result-content">
        <section className="completion-panel" aria-labelledby="completion-title">
          <span className="completion-icon" aria-hidden="true">✓</span>
          <div>
            <span>Assessment status</span>
            <h2 id="completion-title">Preliminary Assessment Generated</h2>
            <p>Unavailable results identify evidence or site information still required.</p>
          </div>
          <StatusBadge value={displayLabel(result.assessmentStatus)} />
        </section>

        {result.isDemoData && (
          <InfoNotice title="Unvalidated ruleset in use" tone="warning">
            <p>Results use configured values that have not been validated as engineering data. They must not be used for construction.</p>
          </InfoNotice>
        )}

        <ResultSection title="Property Summary" eyebrow="Information provided">
          <dl className="property-summary-grid">
            <div><dt>Location / Locality</dt><dd>{input.location}</dd></div>
            {result.derived.normalizedLocation && (
              <div>
                <dt>Resolved Rainfall Location</dt>
                <dd>{result.derived.normalizedLocation.canonicalName}</dd>
              </div>
            )}
            <div><dt>Roof Area</dt><dd>{input.roofAreaM2} m²</dd></div>
            <div><dt>Roof Material</dt><dd>{displayLabel(input.roofMaterial)}</dd></div>
            <div><dt>Available Ground Area</dt><dd>{input.availableGroundAreaM2} m²</dd></div>
            {input.storageCapacityLitres != null && <div><dt>Tank Capacity Used for Recharge Water Balance</dt><dd>{input.storageCapacityLitres} litres</dd></div>}
            <div><dt>Building Basement</dt><dd>{input.buildingHasBasement === undefined ? "Not provided" : input.buildingHasBasement ? "Yes" : "No"}</dd></div>
          </dl>
        </ResultSection>

        <div className="result-two-column">
          <ResultSection title="Rooftop Rainwater Harvesting" eyebrow="Annual potential" className="harvest-section">
            <p className="metric-label">Estimated Harvestable Rainwater</p>
            <MetricValue amount={result.rtrwh.potentialLitresPerYear} unit="L/year" />
            <dl className="supporting-values">
              <div><dt>Annual rainfall used</dt><dd>{value(result.derived.annualRainfallMm, " mm/year")}</dd></div>
              <div><dt>Runoff coefficient</dt><dd>{result.derived.runoffCoefficient ?? "Unavailable"}</dd></div>
              <div><dt>Roof area</dt><dd>{input.roofAreaM2} m²</dd></div>
            </dl>
            <details className="calculation-details">
              <summary>How was this calculated?</summary>
              <div>
                <p>Roof area × annual rainfall × runoff coefficient = estimated harvestable rainwater.</p>
                <div className="formula-row">
                  <span>{input.roofAreaM2} m²</span><b>×</b><span>{value(result.derived.annualRainfallMm, " mm")}</span><b>×</b><span>{result.derived.runoffCoefficient ?? "Unavailable"}</span><b>=</b><strong>{value(result.rtrwh.potentialLitresPerYear, " L/year")}</strong>
                </div>
                <small>Rainfall source: {result.derived.rainfallSource ?? "Not configured"}</small>
                {result.derived.rainfall?.referencePeriod && (
                  <small>Reference period: {result.derived.rainfall.referencePeriod}</small>
                )}
                {result.derived.rainfall?.spatialResolution && (
                  <small>Resolution: {result.derived.rainfall.spatialResolution}</small>
                )}
                {result.derived.rainfall?.sourceUrl && (
                  <small><a href={result.derived.rainfall.sourceUrl} target="_blank" rel="noreferrer">View rainfall source</a></small>
                )}
                {result.derived.rainfall?.message && <p>{result.derived.rainfall.message}</p>}
                {result.derived.runoffCoefficientEvidence?.message && <p>{result.derived.runoffCoefficientEvidence.message}</p>}
                {result.formula.grossRainfallVolumeLitres != null && (
                  <p>Gross rainfall volume: {value(result.formula.grossRainfallVolumeLitres, " L/year")}. Estimated losses represented by the runoff coefficient: {value(result.formula.estimatedLossesLitres ?? null, " L/year")}.</p>
                )}
                {result.formula.methodId && <small>Method: {result.formula.methodId}</small>}
              </div>
            </details>
          </ResultSection>

          <ResultSection title="Recommended RTRWH Size" eyebrow="Indicative storage">
            <p className="metric-label">Indicative RTRWH Size</p>
            <MetricValue amount={result.rtrwh.recommendedSizeLitres} unit="litres" />
            {result.rtrwh.recommendedSizeLitres != null && (
              <dl className="supporting-values single-column">
                <div><dt>Planned monthly use</dt><dd>{value(result.rtrwh.demandUsedLitresPerMonth ?? null, " L/month")}</dd></div>
                <div><dt>Modeled normal-year supply</dt><dd>{value(result.rtrwh.estimatedSupplyLitres ?? null, " L/year")}</dd></div>
                <div><dt>Modeled overflow</dt><dd>{value(result.rtrwh.estimatedOverflowLitres ?? null, " L/year")}</dd></div>
                <div><dt>Normal-year demand met</dt><dd>{value(result.rtrwh.demandMetPercent ?? null, "%")}</dd></div>
              </dl>
            )}
            {result.rtrwh.sizingMessage && (
              <p className={result.rtrwh.recommendedSizeLitres == null ? "unavailable-message" : "section-note"}>{result.rtrwh.sizingMessage}</p>
            )}
            {result.rtrwh.sizingRainfallResolution && <p className="section-note">Rainfall input: {result.rtrwh.sizingRainfallResolution}. Design period: {result.rtrwh.sizingDesignPeriod}.</p>}
          </ResultSection>
        </div>

        <div className="result-two-column">
          <ResultSection title="Artificial Recharge Assessment" eyebrow="Site suitability">
            <div className="status-metric">
              <span>Artificial Recharge Potential</span>
              <StatusBadge value={displayLabel(rechargeStatus)} />
            </div>
            <dl className="supporting-values single-column">
              <div><dt>Water potentially available for recharge</dt><dd>{value(result.artificialRecharge.potentialRechargeLitresPerYear, " L/year")}</dd></div>
              {result.artificialRecharge.annualDemandSuppliedLitres != null && <div><dt>Water supplied from storage</dt><dd>{value(result.artificialRecharge.annualDemandSuppliedLitres, " L/year")}</dd></div>}
              {result.artificialRecharge.annualOverflowLitres != null && <div><dt>Tank overflow</dt><dd>{value(result.artificialRecharge.annualOverflowLitres, " L/year")}</dd></div>}
              {result.artificialRecharge.endingStorageLitres != null && <div><dt>Storage remaining at year end</dt><dd>{value(result.artificialRecharge.endingStorageLitres, " L")}</dd></div>}
            </dl>
            {arMessage && <p className="unavailable-message">{arMessage}</p>}
            {result.artificialRecharge.criteria && result.artificialRecharge.criteria.length > 0 && (
              <details className="calculation-details">
                <summary>Why is this the current result?</summary>
                <div>
                  <ul>
                    {result.artificialRecharge.criteria.map((criterion) => (
                      <li key={criterion.criterion}>
                        <strong>{displayLabel(criterion.criterion)}:</strong> {criterion.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              </details>
            )}
            {result.artificialRecharge.quantityMethodId && <p className="section-note">Water-balance method: {result.artificialRecharge.quantityMethodId}. Overflow is water available for routing, not confirmed aquifer recharge.</p>}
            <p className="section-note">This is a preliminary on-spot assessment and does not replace site-specific hydrogeological investigation.</p>
          </ResultSection>

          <ResultSection title="AR Structure Assessment" eyebrow="Conditional, indicative result">
            <div className="structure-summary">
              <div><span>Selection status</span><strong>{displayLabel(result.artificialRecharge.structureSelectionStatus ?? null)}</strong></div>
              <div><span>Structure option</span><strong>{result.artificialRecharge.recommendedStructure?.displayName ?? "Unavailable"}</strong></div>
              <div><span>Sizing status</span><strong>{displayLabel(result.artificialRecharge.sizingStatus ?? null)}</strong></div>
              <div><span>Published indicative dimensions</span><strong><Dimensions dimensions={result.artificialRecharge.dimensions} /></strong></div>
              {result.artificialRecharge.requiredFootprintM2 != null && <div><span>Internal footprint</span><strong>{result.artificialRecharge.requiredFootprintM2} m²</strong></div>}
            </div>
            {result.artificialRecharge.selectionReasons && result.artificialRecharge.selectionReasons.length > 0 && (
              <div className="section-note"><strong>Why this structure</strong><ul>{result.artificialRecharge.selectionReasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>
            )}
            {result.artificialRecharge.rejectedStructures && result.artificialRecharge.rejectedStructures.length > 0 && (
              <details className="calculation-details"><summary>Rejected alternatives</summary><div><ul>{result.artificialRecharge.rejectedStructures.map((item) => <li key={`${item.structure}-${item.reason}`}><strong>{displayLabel(item.structure)}:</strong> {item.reason}</li>)}</ul></div></details>
            )}
            {result.artificialRecharge.alternativeStructures && result.artificialRecharge.alternativeStructures.length > 0 && (
              <div className="section-note">
                <strong>Other conditionally feasible options</strong>
                <ul>{result.artificialRecharge.alternativeStructures.map((structure) => <li key={structure}>{displayLabel(structure)}</li>)}</ul>
                <p>Final selection requires the stated field verification.</p>
              </div>
            )}
            {result.artificialRecharge.filterMedia && result.artificialRecharge.filterMedia.length > 0 && (
              <details className="calculation-details"><summary>Filter and media requirements</summary><div><ul>{result.artificialRecharge.filterMedia.map((item) => <li key={item}>{item}</li>)}</ul></div></details>
            )}
            {result.artificialRecharge.fieldVerificationRequired && result.artificialRecharge.fieldVerificationRequired.length > 0 && (
              <InfoNotice title="Field verification required" tone="warning"><ul>{result.artificialRecharge.fieldVerificationRequired.map((item) => <li key={item}>{item}</li>)}</ul></InfoNotice>
            )}
            {!result.artificialRecharge.recommendedStructure && (
              <p className="unavailable-message">{arMessage ?? "A validated structure-selection rule is not currently available for this property configuration."}</p>
            )}
          </ResultSection>
        </div>

        {environmental && (
          <ResultSection title="Environmental Evidence" eyebrow="Artificial recharge inputs">
            <dl className="property-summary-grid">
              <div>
                <dt>Groundwater observation</dt>
                <dd>
                  {environmental.groundwater.observation
                    ? `${environmental.groundwater.observation.depthBelowGroundLevelM} m bgl at ${environmental.groundwater.observation.stationName}`
                    : displayLabel(environmental.groundwater.status)}
                </dd>
              </div>
              <div><dt>Groundwater data quality</dt><dd>{displayLabel(environmental.groundwater.status)}</dd></div>
              <div><dt>Regional soil / infiltration proxy</dt><dd>{environmental.soil.information?.soilTexture ?? environmental.soil.information?.soilClass ?? displayLabel(environmental.soil.status)}</dd></div>
              <div><dt>Regional geology</dt><dd>{environmental.hydrogeology.information?.geology ?? displayLabel(environmental.hydrogeology.geologyStatus)}</dd></div>
              <div><dt>Regional geomorphology</dt><dd>{environmental.hydrogeology.information?.geomorphology ?? displayLabel(environmental.hydrogeology.geomorphologyStatus)}</dd></div>
              <div><dt>Regional aquifer / prospects</dt><dd>{environmental.hydrogeology.information?.aquiferType ?? environmental.hydrogeology.information?.groundwaterProspect ?? displayLabel(environmental.hydrogeology.aquiferStatus)}</dd></div>
              <div><dt>Water-quality verification</dt><dd>{waterQualityCriterion ? displayLabel(waterQualityCriterion.result) : "Unavailable"}</dd></div>
            </dl>
            {environmental.groundwater.observation && (
              <p className="section-note">
                Observation period: {environmental.groundwater.observation.observationDate ?? environmental.groundwater.observation.observationPeriod ?? "Not specified"}; approximate distance from property: {value(environmental.groundwater.observation.distanceFromPropertyM, " m")}. This nearby observation is not the exact water level at the property.
              </p>
            )}
            {result.artificialRecharge.fieldTestsRecommended && result.artificialRecharge.fieldTestsRecommended.length > 0 && (
              <InfoNotice title="Site tests required" tone="warning"><ul>{result.artificialRecharge.fieldTestsRecommended.map((item) => <li key={item}>{item}</li>)}</ul></InfoNotice>
            )}
            {environmental.soil.information && (
              <p className="section-note">The displayed soil is regional mapped evidence. Measured property infiltration: {environmental.soil.information.measuredInfiltrationRateMmPerHr == null ? "not available" : `${environmental.soil.information.measuredInfiltrationRateMmPerHr} mm/hour`}.</p>
            )}
            {waterQualityCriterion && <p className="section-note">{waterQualityCriterion.reason}</p>}
            <p className="section-note">{environmental.soil.message}</p>
            <p className="section-note">{environmental.hydrogeology.message}</p>
          </ResultSection>
        )}

        <ResultSection title="Overall Assessment" eyebrow="Summary status" className="overall-section">
          <div className="overall-summary">
            <p>{result.rtrwhSuitability === "SUITABLE" ? "The property shows preliminary potential for rooftop rainwater harvesting based on the configured dataset and rules." : "More configured engineering data is required to complete the rooftop rainwater assessment."}</p>
            <div className="status-table">
              <div><span>RTRWH suitability</span><StatusBadge value={displayLabel(result.rtrwhSuitability)} /></div>
              <div><span>AR suitability</span><StatusBadge value={displayLabel(rechargeStatus)} /></div>
              <div><span>Data completeness</span><StatusBadge value={displayLabel(result.dataCompleteness)} /></div>
            </div>
          </div>
        </ResultSection>

        {result.sources && result.sources.length > 0 && (
          <ResultSection title="Methods and Sources" eyebrow="Provenance">
            <p className="section-note">Sources listed here support the methods and data requirements shown in this assessment. Their presence does not mean an unavailable site value was inferred.</p>
            <ul>
              {result.sources.map((source) => (
                <li key={source.sourceId}>
                  <a href={source.sourceUrl}>{source.authority}: {source.documentTitle}</a>
                  {source.section ? ` — ${source.section}` : ""}
                  {source.page ? `, page ${source.page}` : ""}
                </li>
              ))}
            </ul>
          </ResultSection>
        )}

        <InfoNotice title="Important disclaimer" tone="warning">
          <p>This tool provides a preliminary assessment based on the information provided and configured engineering datasets/rules. Final construction should follow applicable government guidelines and, where necessary, professional site assessment.</p>
        </InfoNotice>

        <div className="result-actions">
          <Link className="button button-primary" href="/">Return Home</Link>
        </div>
      </div>
    </main>
  );
}
