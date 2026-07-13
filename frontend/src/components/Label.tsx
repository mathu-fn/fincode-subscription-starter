import type { ReactNode } from "react";

import { labelClass } from "../lib/styles";

// 等幅+大文字+レタースペーシングのラベル / キャプション（DESIGN の .label）。
// スペック表記・小見出し・メタ情報の見出しに使う。本文には使わない。
type LabelProps = {
  children: ReactNode;
  className?: string;
};

export function Label({ children, className }: LabelProps) {
  return <span className={`${labelClass}${className ? ` ${className}` : ""}`}>{children}</span>;
}
