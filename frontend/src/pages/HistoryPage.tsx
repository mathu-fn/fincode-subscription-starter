import { useEffect, useState } from "react";

import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingButton } from "../components/LoadingButton";
import { apiFetch, ApiError } from "../lib/apiClient";

type HistoryItem = {
  id: number;
  status: string;
  amount: number;
  fincode_payment_id: string | null;
  charged_at: string;
};

type PaginatedBillingHistory = {
  data: HistoryItem[];
  page: number;
  per_page: number;
  total: number;
};

const PER_PAGE = 10;
const pageClass = "mx-auto grid max-w-5xl gap-6";

export function HistoryPage() {
  const [page, setPage] = useState(1);
  const [history, setHistory] = useState<PaginatedBillingHistory | null>(null);
  const [loadingPage, setLoadingPage] = useState(true);
  const [pagingDirection, setPagingDirection] = useState<"prev" | "next" | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);

  useEffect(() => {
    setLoadingPage(true);
    apiFetch<PaginatedBillingHistory>(`/api/subscription/history?page=${page}&per_page=${PER_PAGE}`)
      .then(setHistory)
      .catch((e) => setError(e as ApiError))
      .finally(() => {
        setLoadingPage(false);
        setPagingDirection(null);
      });
  }, [page]);

  const totalPages = history ? Math.max(1, Math.ceil(history.total / history.per_page)) : 1;

  return (
    <section className={pageClass}>
      <h1 className="text-3xl font-bold text-sky-950">決済履歴</h1>
      <ErrorBanner error={error} />
      {!history ? (
        <p className="text-slate-600">読み込み中...</p>
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
              {history.data.map((r) => (
                <tr key={r.id}>
                  <td className="border-b border-sky-100 px-4 py-3 text-sm text-slate-800">
                    {new Date(r.charged_at).toLocaleString("ja-JP")}
                  </td>
                  <td className="border-b border-sky-100 px-4 py-3 text-sm text-slate-800">{r.status}</td>
                  <td className="border-b border-sky-100 px-4 py-3 text-sm font-semibold text-slate-900">¥{r.amount.toLocaleString()}</td>
                  <td className="border-b border-sky-100 px-4 py-3 text-sm text-slate-500">{r.fincode_payment_id ?? "-"}</td>
                </tr>
              ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-center gap-4">
            <LoadingButton
              type="button"
              variant="ghost"
              className="border-sky-200 bg-white px-4 py-2 text-sky-700 hover:bg-sky-50"
              disabled={page === 1 || loadingPage}
              isLoading={pagingDirection === "prev"}
              loadingLabel="読込中..."
              onClick={() => {
                setPagingDirection("prev");
                setPage((p) => p - 1);
              }}
            >
              前へ
            </LoadingButton>
            <span className="text-sm font-semibold text-slate-700">
              {history.page} / {totalPages}
            </span>
            <LoadingButton
              type="button"
              variant="ghost"
              className="border-sky-200 bg-white px-4 py-2 text-sky-700 hover:bg-sky-50"
              disabled={page >= totalPages || loadingPage}
              isLoading={pagingDirection === "next"}
              loadingLabel="読込中..."
              onClick={() => {
                setPagingDirection("next");
                setPage((p) => p + 1);
              }}
            >
              次へ
            </LoadingButton>
          </div>
        </>
      )}
    </section>
  );
}
