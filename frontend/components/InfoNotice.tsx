import type { ReactNode } from "react";

type InfoNoticeProps = {
  title: string;
  children: ReactNode;
  tone?: "info" | "warning" | "error";
  className?: string;
};

export function InfoNotice({ title, children, tone = "info", className = "" }: InfoNoticeProps) {
  return (
    <aside className={`info-notice info-notice-${tone} ${className}`.trim()} role={tone === "error" ? "alert" : undefined}>
      <span className="notice-symbol" aria-hidden="true">i</span>
      <div>
        <strong>{title}</strong>
        <div className="notice-content">{children}</div>
      </div>
    </aside>
  );
}
