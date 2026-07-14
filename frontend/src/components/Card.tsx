import type { ReactNode } from "react";

// OS ウィジェット風のフラットなカード: 1px 薄グレー枠、影・グラデーションなし。
// padding はページ毎に異なるため既定では付けず、className で付与する（例: p-4 / p-6）。
type CardProps = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className }: CardProps) {
  return (
    <div className={`border border-line bg-white${className ? ` ${className}` : ""}`}>{children}</div>
  );
}
