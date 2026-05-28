import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ConfirmDialog } from "../components/ConfirmDialog";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingButton } from "../components/LoadingButton";
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

const pageClass = "mx-auto grid max-w-5xl gap-6";
const cardClass = "border border-sky-200 bg-white p-6 shadow-sm shadow-sky-100";
const primaryLinkClass =
  "inline-flex min-h-11 items-center justify-center border border-sky-600 bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2";

export function SubscriptionPage() {
  const [sub, setSub] = useState<Subscription>(null);
  const [loaded, setLoaded] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
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

  async function confirmCancel() {
    if (!sub) return;
    setCancelling(true);
    setError(null);
    try {
      const updated = await apiFetch<Subscription>("/api/subscription", { method: "DELETE" });
      setSub(updated);
      setConfirmOpen(false);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setCancelling(false);
    }
  }

  return (
    <section className={pageClass}>
      <h1 className="text-3xl font-bold text-sky-950">サブスクリプション詳細</h1>
      <ErrorBanner error={error} />
      {!loaded ? (
        <p className="text-slate-600">読み込み中...</p>
      ) : !sub ? (
        <article className={cardClass}>
          <p className="text-slate-700">アクティブな契約はありません。</p>
          <p className="mt-4">
            <Link to="/plans" className={primaryLinkClass}>
              プランを選ぶ
            </Link>
          </p>
        </article>
      ) : (
        <article className={cardClass}>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="bg-sky-50 p-4">
              <dt className="text-sm text-slate-500">プラン</dt>
              <dd className="mt-1 font-semibold text-slate-900">{sub.plan_name}</dd>
            </div>
            <div className="bg-sky-50 p-4">
              <dt className="text-sm text-slate-500">金額</dt>
              <dd className="mt-1 font-semibold text-slate-900">¥{sub.plan_amount.toLocaleString()} / {sub.plan_interval}</dd>
            </div>
            <div className="bg-sky-50 p-4">
              <dt className="text-sm text-slate-500">状態</dt>
              <dd className="mt-1 font-semibold text-slate-900">{sub.status}</dd>
            </div>
            <div className="bg-sky-50 p-4">
              <dt className="text-sm text-slate-500">契約日</dt>
              <dd className="mt-1 font-semibold text-slate-900">{new Date(sub.created_at).toLocaleString("ja-JP")}</dd>
            </div>
            {sub.cancelled_at && (
              <div className="bg-sky-50 p-4">
                <dt className="text-sm text-slate-500">解約日</dt>
                <dd className="mt-1 font-semibold text-slate-900">{new Date(sub.cancelled_at).toLocaleString("ja-JP")}</dd>
              </div>
            )}
          </dl>
          {sub.status === "active" && (
            <p className="mt-6">
              <LoadingButton
                type="button"
                variant="danger"
                isLoading={cancelling}
                loadingLabel="解約中..."
                onClick={() => setConfirmOpen(true)}
              >
                解約する
              </LoadingButton>
            </p>
          )}
        </article>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title="サブスクリプションを解約しますか？"
        description={
          sub ? (
            <>
              <p>
                プラン「{sub.plan_name}」（¥{sub.plan_amount.toLocaleString()} / {sub.plan_interval}）を解約します。
              </p>
              <p className="mt-2 text-slate-500">解約後は再度プラン選択が必要になります。</p>
            </>
          ) : null
        }
        confirmLabel="解約する"
        loadingLabel="解約中..."
        variant="danger"
        isConfirming={cancelling}
        onConfirm={confirmCancel}
        onCancel={() => setConfirmOpen(false)}
      />
    </section>
  );
}
