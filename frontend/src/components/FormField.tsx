import type { ReactNode } from "react";

import { fieldClass, labelClass } from "../lib/styles";

// ラベル（等幅大文字キャプション）+ 任意のコントロール（input / select 等）をまとめる。
// ラッパーはレイアウトのみ（fieldClass）にし、キャプションの text-transform や
// letter-spacing がコントロールへ継承漏れしないよう文字スタイルは span に閉じる。
type FormFieldProps = {
  label: ReactNode;
  htmlFor?: string;
  children: ReactNode;
  className?: string;
};

export function FormField({ label, htmlFor, children, className }: FormFieldProps) {
  return (
    <label htmlFor={htmlFor} className={`${fieldClass}${className ? ` ${className}` : ""}`}>
      <span className={labelClass}>{label}</span>
      {children}
    </label>
  );
}
