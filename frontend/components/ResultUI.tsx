import type { ReactNode } from "react";

export function StatusBadge({ value }: { value: string | null }) {
  const normalized = (value ?? "unavailable").toLowerCase().replaceAll(/[_\s]+/g, "-");
  return <span className={`status-badge status-${normalized}`}>{value ?? "Unavailable"}</span>;
}

export function ResultSection({
  title,
  eyebrow,
  children,
  className = "",
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`result-section ${className}`.trim()}>
      <header className="section-titlebar">
        <div>
          {eyebrow && <span>{eyebrow}</span>}
          <h2>{title}</h2>
        </div>
      </header>
      <div className="section-body">{children}</div>
    </section>
  );
}
