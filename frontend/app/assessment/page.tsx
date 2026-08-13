"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { AssessmentInput } from "@/lib/types";
import { FormField } from "@/components/FormField";
import { InfoNotice } from "@/components/InfoNotice";
import { SERVER_SNAPSHOT, useSessionValue } from "@/lib/session";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function apiErrorMessage(body: unknown): string {
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return "We could not complete the assessment. Please review the information and try again.";
  }
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object" && "msg" in detail[0]) {
    return String(detail[0].msg).replace(/^Value error, /, "");
  }
  return "We could not complete the assessment. Please review the information and try again.";
}

export default function AssessmentPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const storedInputs = useSessionValue("rainassess-inputs");
  const storedResult = useSessionValue("rainassess-result");

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, []);

  let savedInputs: AssessmentInput | null = null;
  if (storedInputs !== SERVER_SNAPSHOT && storedResult !== SERVER_SNAPSHOT) {
    try {
      savedInputs = storedInputs
        ? JSON.parse(storedInputs)
        : storedResult
          ? JSON.parse(storedResult).inputs
          : null;
    } catch {
      savedInputs = null;
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const payload = {
      location: form.get("location"),
      roofAreaM2: Number(form.get("roofAreaM2")),
      roofMaterial: form.get("roofMaterial"),
      soilType: form.get("soilType"),
      groundwaterDepthM: Number(form.get("groundwaterDepthM")),
      availableGroundAreaM2: Number(form.get("availableGroundAreaM2")),
    };

    try {
      const response = await fetch(`${apiUrl}/api/assessment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(apiErrorMessage(await response.json().catch(() => null)));
      }
      const result = await response.json();
      sessionStorage.setItem("rainassess-inputs", JSON.stringify(payload));
      sessionStorage.setItem("rainassess-result", JSON.stringify(result));
      router.push("/result");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We could not complete the assessment. Please try again.");
      setSubmitting(false);
    }
  }

  if (storedInputs === SERVER_SNAPSHOT || storedResult === SERVER_SNAPSHOT) {
    return <main className="page-main"><div className="shell loading-state" role="status">Loading your property information…</div></main>;
  }

  return (
    <main className="page-main">
      <div className="page-title-band">
        <div className="shell">
          <span className="breadcrumb">Home <b aria-hidden="true">/</b> Assessment</span>
          <h1>Property Assessment</h1>
          <p>Provide basic information about your property to estimate rooftop rainwater harvesting and artificial recharge potential.</p>
        </div>
      </div>

      <div className="shell page-content assessment-layout">
        <form className="service-form" onSubmit={submit}>
          <div className="form-card">
            <header className="form-section-heading">
              <span>1</span>
              <div><h2>Property and rooftop details</h2><p>Information used to estimate available rooftop runoff.</p></div>
            </header>
            <div className="form-grid">
              <FormField id="location" label="Location / Locality" helper="Select a city available in the configured development rainfall dataset." className="field-wide">
                <select id="location" name="location" required defaultValue={savedInputs?.location ?? ""} aria-describedby="location-help">
                  <option value="" disabled>Select city / locality</option>
                  <option value="Bengaluru">Bengaluru</option>
                  <option value="Chennai">Chennai</option>
                  <option value="Delhi">Delhi</option>
                  <option value="Hyderabad">Hyderabad</option>
                  <option value="Mumbai">Mumbai</option>
                </select>
              </FormField>
              <FormField id="roofAreaM2" label="Roof Area" helper="Enter the approximate rooftop catchment area.">
                <div className="control-with-unit"><input id="roofAreaM2" name="roofAreaM2" type="number" min="0.1" max="100000" step="0.1" required defaultValue={savedInputs?.roofAreaM2 ?? ""} aria-describedby="roofAreaM2-help" /><span>m²</span></div>
              </FormField>
              <FormField id="roofMaterial" label="Roof Material" helper="Used to look up the configured runoff coefficient.">
                <select id="roofMaterial" name="roofMaterial" required defaultValue={savedInputs?.roofMaterial ?? ""} aria-describedby="roofMaterial-help">
                  <option value="" disabled>Select roof material</option><option value="RCC">RCC / Concrete</option><option value="TILES">Tiles</option><option value="METAL">Metal sheet</option><option value="OTHER">Other</option><option value="DONT_KNOW">Don&apos;t know</option>
                </select>
              </FormField>
            </div>
          </div>

          <div className="form-card">
            <header className="form-section-heading">
              <span>2</span>
              <div><h2>Ground and recharge details</h2><p>Basic site conditions used for the preliminary recharge assessment.</p></div>
            </header>
            <div className="form-grid form-grid-three">
              <FormField id="soilType" label="Soil Type" helper="Select “Don't know” if you are unsure.">
                <select id="soilType" name="soilType" required defaultValue={savedInputs?.soilType ?? ""} aria-describedby="soilType-help">
                  <option value="" disabled>Select soil type</option><option value="SANDY">Sandy</option><option value="SANDY_LOAM">Sandy Loam</option><option value="LOAM">Loam</option><option value="CLAYEY">Clayey</option><option value="ROCKY">Rocky</option><option value="DONT_KNOW">Don&apos;t know</option>
                </select>
              </FormField>
              <FormField id="groundwaterDepthM" label="Groundwater Depth" helper="Approximate depth from ground surface to groundwater level.">
                <div className="control-with-unit"><input id="groundwaterDepthM" name="groundwaterDepthM" type="number" min="0" max="1000" step="0.1" required defaultValue={savedInputs?.groundwaterDepthM ?? ""} aria-describedby="groundwaterDepthM-help" /><span>metres</span></div>
              </FormField>
              <FormField id="availableGroundAreaM2" label="Available Ground Area" helper="Open area that could accommodate a recharge structure.">
                <div className="control-with-unit"><input id="availableGroundAreaM2" name="availableGroundAreaM2" type="number" min="0" max="100000" step="0.1" required defaultValue={savedInputs?.availableGroundAreaM2 ?? ""} aria-describedby="availableGroundAreaM2-help" /><span>m²</span></div>
              </FormField>
            </div>
          </div>

          {error && <InfoNotice title="Assessment could not be completed" tone="error" className="form-message"><p>{error}</p></InfoNotice>}

          <div className="form-actionbar">
            <p>Fields marked <span aria-hidden="true">*</span> are required. Your results are preliminary.</p>
            <button className="button button-primary submit-button" type="submit" disabled={submitting} aria-live="polite">
              {submitting ? <><span className="loading-dot" aria-hidden="true" /> Calculating assessment…</> : <>Calculate Assessment <span aria-hidden="true">→</span></>}
            </button>
          </div>
        </form>

        <aside className="assessment-sidebar" aria-label="Assessment guidance">
          <h2>Before you begin</h2>
          <ul>
            <li>Use the horizontal catchment area of your roof.</li>
            <li>Approximate site values are acceptable for this preliminary assessment.</li>
            <li>No household demand or consumption data is required.</li>
          </ul>
          <InfoNotice title="Data use">
            <p>Your entries are used only to calculate the current assessment and are retained in this browser session.</p>
          </InfoNotice>
        </aside>
      </div>
    </main>
  );
}
