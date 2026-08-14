import type { ReactNode } from "react";

export function FormField({
  id,
  label,
  helper,
  children,
  className = "",
  required = true,
}: {
  id: string;
  label: string;
  helper?: string;
  children: ReactNode;
  className?: string;
  required?: boolean;
}) {
  const helperId = helper ? `${id}-help` : undefined;
  return (
    <div className={`form-field ${className}`.trim()}>
      <label htmlFor={id}>{label}{required && <span aria-hidden="true"> *</span>}</label>
      {children}
      {helper && <p id={helperId} className="field-help">{helper}</p>}
    </div>
  );
}
