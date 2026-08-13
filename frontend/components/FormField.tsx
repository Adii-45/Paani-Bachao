import type { ReactNode } from "react";

export function FormField({
  id,
  label,
  helper,
  children,
  className = "",
}: {
  id: string;
  label: string;
  helper?: string;
  children: ReactNode;
  className?: string;
}) {
  const helperId = helper ? `${id}-help` : undefined;
  return (
    <div className={`form-field ${className}`.trim()}>
      <label htmlFor={id}>{label}<span aria-hidden="true"> *</span></label>
      {children}
      {helper && <p id={helperId} className="field-help">{helper}</p>}
    </div>
  );
}
