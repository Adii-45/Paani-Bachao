import Link from "next/link";
import { InfoNotice } from "@/components/InfoNotice";

const steps = [
  {
    number: "01",
    title: "Enter Property Details",
    text: "Provide your location, roof area, roof material and basic site information.",
  },
  {
    number: "02",
    title: "Assessment",
    text: "Configured rainfall data and deterministic engineering rules are applied to your inputs.",
  },
  {
    number: "03",
    title: "View Recommendation",
    text: "Review indicative RTRWH sizing, recharge potential and an AR structure recommendation where available.",
  },
];

export default function Home() {
  return (
    <main>
      <section className="service-hero">
        <div className="shell hero-layout">
          <div className="hero-content">
            <span className="service-label">Rainwater &amp; Groundwater Assessment Platform</span>
            <h1>Assess Your Home&apos;s Rainwater Harvesting Potential</h1>
            <p>
              Estimate rooftop rainwater harvesting potential, groundwater recharge suitability,
              and indicative structure sizes using basic property information.
            </p>
            <div className="hero-actions">
              <Link className="button button-primary" href="/assessment">Start Assessment <span aria-hidden="true">→</span></Link>
              <Link className="button button-outline" href="#how-it-works">How It Works</Link>
            </div>
            <div className="service-facts" aria-label="Service details">
              <span><b>No login</b> required</span>
              <span><b>6 property</b> inputs</span>
              <span><b>Deterministic</b> assessment</span>
            </div>
          </div>

          <div className="hero-service-card" aria-label="Assessment outputs">
            <div className="hero-card-heading">
              <span className="water-symbol" aria-hidden="true">≈</span>
              <div><small>Assessment service</small><strong>What you will receive</strong></div>
            </div>
            <ul>
              <li><span>01</span>Annual rooftop harvesting potential</li>
              <li><span>02</span>Indicative RTRWH storage size</li>
              <li><span>03</span>Artificial recharge suitability</li>
              <li><span>04</span>AR structure and approximate dimensions</li>
            </ul>
            <p>Results are shown with the rainfall and runoff values used.</p>
          </div>
        </div>
      </section>

      <section className="process-section" id="how-it-works">
        <div className="shell">
          <div className="section-heading">
            <span>Assessment process</span>
            <h2>How the service works</h2>
            <p>A short, transparent workflow designed for residential property owners.</p>
          </div>
          <div className="process-grid">
            {steps.map((step) => (
              <article className="process-card" key={step.number}>
                <span className="step-number">{step.number}</span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="about-section" id="about">
        <div className="shell about-layout">
          <div className="about-copy">
            <span className="section-kicker">About the assessment</span>
            <h2>Clear estimates based on configured data and rules</h2>
            <p>
              RainAssess combines property information with configured rainfall and engineering
              rules. Calculations are deterministic, reproducible and kept separate from the user interface.
            </p>
          </div>
          <InfoNotice title="Important information">
            <p>This tool provides a preliminary on-spot assessment. Final construction and engineering decisions should follow applicable technical guidelines and site-specific professional assessment.</p>
          </InfoNotice>
        </div>
      </section>
    </main>
  );
}
