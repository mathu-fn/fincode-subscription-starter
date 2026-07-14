import type { ReactNode } from "react";

import { Label } from "../../components/Label";
import { Skeleton } from "../../components/Skeleton";

// ダッシュボード上部の「一目でわかる」サマリーカード（契約 / カード / 直近決済）。
// 見出しラベル + 読み込み中スケルトン + 本文、の同型を 1 箇所に集約する。
type SummaryCardProps = {
  label: string;
  loading: boolean;
  children: ReactNode;
};

export function SummaryCard({ label, loading, children }: SummaryCardProps) {
  return (
    <article className="grid min-h-28 gap-1.5 border border-line bg-white p-4">
      <Label>{label}</Label>
      {loading ? (
        <>
          <Skeleton className="mt-1 h-7 w-3/4" />
          <Skeleton className="mt-1 h-4 w-1/2" />
        </>
      ) : (
        children
      )}
    </article>
  );
}
