import type { InputHTMLAttributes } from "react";

import { inputClass, labelClass } from "../lib/styles";

type FormFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
};

export function FormField({ label, ...props }: FormFieldProps) {
  return (
    <label className={labelClass}>
      <span>{label}</span>
      <input className={inputClass} {...props} />
    </label>
  );
}
