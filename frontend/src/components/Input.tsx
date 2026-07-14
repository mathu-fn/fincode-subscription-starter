import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";

import { inputClass } from "../lib/styles";

// Nothing 風のフラットな入力欄: 1px 枠、フォーカスで枠が黒に。角丸・影なし。
type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, ...props },
  ref
) {
  return <input ref={ref} className={`${inputClass}${className ? ` ${className}` : ""}`} {...props} />;
});
