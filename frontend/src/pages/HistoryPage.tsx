import { useEffect, useState } from "react";

import { ErrorBanner } from "../components/ErrorBanner";
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

export function HistoryPage() {
  const [page, setPage] = useState(1);
  const [history, setHistory] = useState<PaginatedBillingHistory | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);

  useEffect(() => {
    apiFetch<PaginatedBillingHistory>(`/api/subscription/history?page=${page}&per_page=${PER_PAGE}`)
      .then(setHistory)
      .catch((e) => setError(e as ApiError));
  }, [page]);

  const totalPages = history ? Math.max(1, Math.ceil(history.total / history.per_page)) : 1;

  return (
    <section className="page">
      <h1>決済履歴</h1>
      <ErrorBanner error={error} />
      {!history ? (
        <p>読み込み中...</p>
      ) : history.data.length === 0 ? (
        <p>履歴はまだありません。</p>
      ) : (
        <>
          <table className="history-table">
            <thead>
              <tr>
                <th>日時</th>
                <th>状態</th>
                <th>金額</th>
                <th>fincode 支払 ID</th>
              </tr>
            </thead>
            <tbody>
              {history.data.map((r) => (
                <tr key={r.id}>
                  <td>{new Date(r.charged_at).toLocaleString("ja-JP")}</td>
                  <td>{r.status}</td>
                  <td>¥{r.amount.toLocaleString()}</td>
                  <td className="muted">{r.fincode_payment_id ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination">
            <button type="button" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
              前へ
            </button>
            <span>
              {history.page} / {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              次へ
            </button>
          </div>
        </>
      )}
    </section>
  );
}
