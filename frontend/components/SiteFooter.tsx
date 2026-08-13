import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="portal-footer">
      <div className="shell footer-main">
        <div>
          <strong>Rainwater &amp; Groundwater Assessment Platform</strong>
          <p>Preliminary assessment tool for rooftop rainwater harvesting and artificial recharge planning.</p>
        </div>
        <nav aria-label="Footer navigation">
          <Link href="/">Home</Link>
          <Link href="/assessment">Start Assessment</Link>
          <Link href="/#about">About</Link>
        </nav>
      </div>
      <div className="footer-base">
        <div className="shell">
          <span>RainAssess MVP</span>
          <span>Indicative results only — professional site assessment may be required.</span>
        </div>
      </div>
    </footer>
  );
}

