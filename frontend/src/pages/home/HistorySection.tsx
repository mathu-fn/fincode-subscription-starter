import { Skeleton } from "../../components/Skeleton";
import { StatusBadge } from "../../components/StatusBadge";
import { secondaryBtn, sectionClass, sectionTitle, specTableClass } from "../../lib/styles";
import type { PaginatedBillingHistory } from "../../types/api";

import { formatDateTime, formatYen } from "./utils";

type HistorySectionProps = {
  history: PaginatedBillingHistory | null;
  page: number;
  totalPages: number;
  onPrevPage: () => void;
  onNextPage: () => void;
};

const headerCellClass =
  "border-b border-line px-4 py-3 text-left font-mono text-xs uppercase tracking-[0.1em] text-muted";
const tableClass = `${specTableClass} min-w-[680px] border-collapse text-left`;

export function HistorySection({
  history,
  page,
  totalPages,
  onPrevPage,
  onNextPage
}: HistorySectionProps) {
  return (
    <section id="history" className={sectionClass}>
      <div className="flex items-center justify-between gap-4">
        <h2 className={sectionTitle}>履歴</h2>
      </div>
      {!history ? (
        <div className="overflow-x-auto border-t border-line">
          <table className={tableClass}>
            <thead>
              <tr>
                <th className={headerCellClass}>日時</th>
                <th className={headerCellClass}>状態</th>
                <th className={headerCellClass}>金額</th>
                <th className={headerCellClass}>fincode 支払 ID</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  <td className="border-b border-line px-4 py-3">
                    <Skeleton className="h-4 w-32" />
                  </td>
                  <td className="border-b border-line px-4 py-3">
                    <Skeleton className="h-4 w-16" />
                  </td>
                  <td className="border-b border-line px-4 py-3">
                    <Skeleton className="h-4 w-20" />
                  </td>
                  <td className="border-b border-line px-4 py-3">
                    <Skeleton className="h-4 w-40" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : history.data.length === 0 ? (
        <p className="text-muted">履歴はまだありません。</p>
      ) : (
        <>
          <div className="overflow-x-auto border-t border-line">
            <table className={tableClass}>
              <thead>
                <tr>
                  <th className={headerCellClass}>日時</th>
                  <th className={headerCellClass}>状態</th>
                  <th className={headerCellClass}>金額</th>
                  <th className={headerCellClass}>fincode 支払 ID</th>
                </tr>
              </thead>
              <tbody>
                {history.data.map((record) => (
                  <tr key={record.id}>
                    <td className="border-b border-line px-4 py-3 text-sm text-black">
                      {formatDateTime(record.charged_at)}
                    </td>
                    <td className="border-b border-line px-4 py-3">
                      <StatusBadge status={record.status} />
                    </td>
                    <td className="border-b border-line px-4 py-3 font-mono text-sm text-black">
                      {formatYen(record.amount)}
                    </td>
                    <td className="border-b border-line px-4 py-3 font-mono text-xs text-muted">
                      {record.fincode_payment_id ?? "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-center gap-4">
            <button
              type="button"
              className={`${secondaryBtn} disabled:cursor-not-allowed disabled:opacity-40`}
              disabled={page === 1}
              onClick={onPrevPage}
            >
              前へ
            </button>
            <span className="font-mono text-xs uppercase tracking-[0.1em] text-muted">
              {history.page} / {totalPages}
            </span>
            <button
              type="button"
              className={`${secondaryBtn} disabled:cursor-not-allowed disabled:opacity-40`}
              disabled={page >= totalPages}
              onClick={onNextPage}
            >
              次へ
            </button>
          </div>
        </>
      )}
    </section>
  );
}
