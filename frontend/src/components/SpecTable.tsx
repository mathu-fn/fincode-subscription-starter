import type { ReactNode } from "react";

import { specRowClass, specTableClass } from "../lib/styles";

// 工業製品の「銘板」風の 1px 罫線テーブル。ラベル（等幅大文字）と値の key/value を、
// 上罫線 + 各行の下罫線だけで見せる。影・背景塗りは使わない。
// 多列のデータ表（決済履歴など）は素の <table> に specTableClass を当てて組む。
type SpecTableProps = {
  children: ReactNode;
  className?: string;
};

export function SpecTable({ children, className }: SpecTableProps) {
  return <dl className={`${specTableClass}${className ? ` ${className}` : ""}`}>{children}</dl>;
}

type SpecRowProps = {
  label: ReactNode;
  children: ReactNode;
  className?: string;
};

export function SpecRow({ label, children, className }: SpecRowProps) {
  return (
    <div className={`${specRowClass}${className ? ` ${className}` : ""}`}>
      <dt className="font-mono text-xs uppercase tracking-[0.1em] text-muted">{label}</dt>
      <dd className="text-right text-sm text-black">{children}</dd>
    </div>
  );
}
