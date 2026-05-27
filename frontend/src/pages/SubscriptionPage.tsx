import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
import { apiFetch, ApiError } from "../lib/apiClient";

type Subscription = {
  id: number;
  status: string;
  plan_name: string;
  plan_amount: number;
  plan_interval: string;
  cancelled_at: string | null;
  current_period_end: string | null;
  created_at: string;
} | null;

export function SubscriptionPage() {
  const [sub, setSub] = useState<Subscription>(null);
  const [loaded, setLoaded] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<ApiError | Error | null>(null);

  async function refresh() {
    try {
      const data = await apiFetch<Subscription>("/api/subscription");
      setSub(data);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setLoaded(true);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onCancel() {
    if (!sub) return;
    if (!confirm("本当に解約しますか？")) return;
    setCancelling(true);
    setError(null);
    try {
      const updated = await apiFetch<Subscription>("/api/subscription", { method: "DELETE" });
      setSub(updated);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setCancelling(false);
    }
  }

  return (
    <section className="page">
      <h1>サブスクリプション詳細</h1>
      <ErrorBanner error={error} />
      {!loaded ? (
        <p>読み込み中...</p>
      ) : !sub ? (
        <article className="card">
          <p>アクティブな契約はありません。</p>
          <p className="actions">
            <Link to="/plans" className="primary-link">
              プランを選ぶ
            </Link>
          </p>
        </article>
      ) : (
        <article className="card">
          <dl className="meta">
            <div>
              <dt>プラン</dt>
              <dd>{sub.plan_name}</dd>
            </div>
            <div>
              <dt>金額</dt>
              <dd>¥{sub.plan_amount.toLocaleString()} / {sub.plan_interval}</dd>
            </div>
            <div>
              <dt>状態</dt>
              <dd>{sub.status}</dd>
            </div>
            <div>
              <dt>契約日</dt>
              <dd>{new Date(sub.created_at).toLocaleString("ja-JP")}</dd>
            </div>
            {sub.cancelled_at && (
              <div>
                <dt>解約日</dt>
                <dd>{new Date(sub.cancelled_at).toLocaleString("ja-JP")}</dd>
              </div>
            )}
          </dl>
          {sub.status === "active" && (
            <p className="actions">
              <button type="button" className="danger" disabled={cancelling} onClick={onCancel}>
                {cancelling ? "解約中..." : "解約する"}
              </button>
            </p>
          )}
        </article>
      )}
    </section>
  );
}
