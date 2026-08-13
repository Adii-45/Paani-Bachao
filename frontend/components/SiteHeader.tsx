import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="portal-header">
      <div className="utility-bar">
        <div className="shell utility-inner">
          <span>Water Conservation Assessment Portal</span>
          <span className="utility-note">Residential rainwater and recharge screening</span>
        </div>
      </div>

      <div className="identity-bar">
        <div className="shell identity-inner">
          <Link className="portal-identity" href="/" aria-label="Paani Bachao home">
            <span className="water-mark" aria-hidden="true">
              <svg viewBox="0 0 48 48" role="img">
                <path d="M24 4C18 13 10 21 10 30a14 14 0 0 0 28 0C38 21 30 13 24 4Z" />
                <path d="M17 31c2 4 6 6 10 5" />
              </svg>
            </span>
            <span className="identity-copy">
              <strong>Paani Bachao</strong>
              <small>Rooftop Rainwater Harvesting &amp; Artificial Recharge</small>
            </span>
          </Link>
          <span className="independence-note">Preliminary household assessment<br /><b>Independent, non-government service</b></span>
        </div>
      </div>

      <nav className="main-nav" aria-label="Primary navigation">
        <div className="shell nav-inner">
          <div className="nav-links">
            <Link href="/">Home</Link>
            <Link href="/assessment">Assessment</Link>
            <Link href="/#about">About the Assessment</Link>
          </div>
          <Link className="nav-cta" href="/assessment">Start Assessment</Link>
        </div>
      </nav>
    </header>
  );
}
