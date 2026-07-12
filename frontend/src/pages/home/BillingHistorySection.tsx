import type { Dispatch, SetStateAction } from "react";

import { Skeleton } from "../../components/Skeleton";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDateTime } from "../../lib/format";
import { sectionClass } from "../../lib/styles";
import type { PaginatedBillingHistory } from "../../types/api";

type BillingHistorySectionProps = {
  history: PaginatedBillingHistory | null;
  page: number;
  totalPages: number;
  setPage: Dispatch<SetStateAction<number>>;
};

export function BillingHistorySection({ history, page, totalPages, setPage }: BillingHistorySectionProps) {
  return (
    <section id="history" className={sectionClass}>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-xl font-bold text-sky-950">履歴</h2>
      </div>
      {!history ? (
        <div className="overflow-x-auto border border-sky-200 bg-white shadow-sm shadow-sky-100">
          <table className="w-full min-w-[680px] border-collapse text-left">
            <thead>
              <tr>
                <th className="border-b border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-slate-600">日時</th>
                <th className="border-b border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-slate-600">状態</th>
                <th className="border-b border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-slate-600">金額</th>
                <th className="border-b border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-slate-600">fincode 支払 ID</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 4 }).map((_, i) => (
                <tr key={i}>
                  <td className="border-b border-sky-100 px-4 py-3">
                    <Skeleton className="h-4 w-32" />
                  </td>
                  <td className="border-b border-sky-100 px-4 py-3">
                    <Skeleton className="h-4 w-16" />
                  </td>
                  <td className="border-b border-sky-100 px-4 py-3">
                    <Skeleton className="h-4 w-20" />
                  </td>
                  <td className="border-b border-sky-100 px-4 py-3">
                    <Skeleton className="h-4 w-40" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : history.data.length === 0 ? (
        <p className="text-slate-700">履歴はまだありません。</p>
      ) : (
        <>
          <div className="overflow-x-auto border border-sky-200 bg-white shadow-sm shadow-sky-100">
            <table className="w-full min-w-[680px] border-collapse text-left">
              <thead>
              <tr>
                <th className="border-b border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-slate-600">日時</th>
                <th className="border-b border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-slate-600">状態</th>
                <th className="border-b border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-slate-600">金額</th>
                <th className="border-b border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-slate-600">fincode 支払 ID</th>
              </tr>
              </thead>
              <tbody>
              {history.data.map((record) => (
                <tr key={record.id}>
                  <td className="border-b border-sky-100 px-4 py-3 text-sm text-slate-800">
                    {formatDateTime(record.charged_at)}
                  </td>
                  <td className="border-b border-sky-100 px-4 py-3 text-sm text-slate-800">
                    <StatusBadge status={record.status} />
                  </td>
                  <td className="border-b border-sky-100 px-4 py-3 text-sm font-semibold text-slate-900">¥{record.amount.toLocaleString()}</td>
                  <td className="border-b border-sky-100 px-4 py-3 text-sm text-slate-500">{record.fincode_payment_id ?? "-"}</td>
                </tr>
              ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-center gap-4">
            <button
              type="button"
              className="min-h-10 border border-sky-200 bg-white px-4 py-2 text-sm font-semibold text-sky-700 transition-colors hover:bg-sky-50 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={page === 1}
              onClick={() => setPage((current) => current - 1)}
            >
              前へ
            </button>
            <span className="text-sm font-semibold text-slate-700">
              {history.page} / {totalPages}
            </span>
            <button
              type="button"
              className="min-h-10 border border-sky-200 bg-white px-4 py-2 text-sm font-semibold text-sky-700 transition-colors hover:bg-sky-50 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={page >= totalPages}
              onClick={() => setPage((current) => current + 1)}
            >
              次へ
            </button>
          </div>
        </>
      )}
    </section>
  );
}
