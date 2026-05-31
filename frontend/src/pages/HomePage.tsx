import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingButton } from "../components/LoadingButton";
import { useAuth } from "../hooks/useAuth";
import { apiFetch, ApiError } from "../lib/apiClient";
import { FincodeUiBundle, initFincodeUi, mountFincodeUi, tokenizeViaUi, unmountFincodeUi } from "../lib/fincodeJs";
import { inputClass, labelClass, pageClass, primaryLinkClass, sectionClass, summaryCardClass } from "../lib/styles";
import type { Subscription, Plan, Card, HistoryItem, PaginatedBillingHistory } from "../types/api";

const FINCODE_MOUNT_ID = "fincode-ui-mount";
const PER_PAGE = 10;
// 0円フリープランの番兵ID（バックエンドの FREE_PLAN_ID と一致）。
const FREE_PLAN_ID = "free";

function formatPlanPrice(amount: number, interval: string): string {
  if (amount === 0) return "無料";
  return `¥${amount.toLocaleString()} / ${interval}`;
}
const cardClass = "border border-sky-200 bg-white p-4 shadow-sm shadow-sky-100";

export function HomePage() {
  const { user } = useAuth();
  const location = useLocation();
  const [sub, setSub] = useState<Subscription>(null);
  const [subscriptionLoaded, setSubscriptionLoaded] = useState(false);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [plansLoaded, setPlansLoaded] = useState(false);
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);
  const [submittingPlan, setSubmittingPlan] = useState<string | null>(null);
  const [cardSubmitting, setCardSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [deletingCardId, setDeletingCardId] = useState<number | null>(null);
  const [showCardForm, setShowCardForm] = useState<boolean>(false);
  const [cardFormLoading, setCardFormLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [history, setHistory] = useState<PaginatedBillingHistory | null>(null);
  const [latestHistory, setLatestHistory] = useState<HistoryItem | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const fincodeRef = useRef<FincodeUiBundle | null>(null);

  const refreshSubscription = useCallback(async () => {
    try {
      const data = await apiFetch<Subscription>("/api/subscription");
      setSub(data);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setSubscriptionLoaded(true);
    }
  }, []);

  const refreshPlansAndCards = useCallback(async () => {
    try {
      const [planList, cardList] = await Promise.all([
        apiFetch<Plan[]>("/api/subscription/plans"),
        apiFetch<Card[]>("/api/subscription/cards")
      ]);
      setPlans(planList);
      setCards(cardList);
      setSelectedCardId((current) => {
        if (current && cardList.some((card) => card.id === current)) return current;
        return cardList[0]?.id ?? null;
      });
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setPlansLoaded(true);
    }
  }, []);

  const refreshHistory = useCallback(async (pageNumber: number) => {
    try {
      const data = await apiFetch<PaginatedBillingHistory>(
        `/api/subscription/history?page=${pageNumber}&per_page=${PER_PAGE}`
      );
      setHistory(data);
      if (pageNumber === 1) {
        setLatestHistory(data.data[0] ?? null);
      }
    } catch (e) {
      setError(e as ApiError);
    }
  }, []);

  useEffect(() => {
    refreshSubscription();
    refreshPlansAndCards();
  }, [refreshPlansAndCards, refreshSubscription]);

  useEffect(() => {
    if (!location.hash) return;
    let id: string;
    try {
      id = decodeURIComponent(location.hash.slice(1));
    } catch {
      return;
    }
    window.requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ block: "start" });
    });
  }, [location.hash]);

  useEffect(() => {
    setHistory(null);
    refreshHistory(page);
  }, [page, refreshHistory]);

  useEffect(() => {
    if (!showCardForm) return;
    let cancelled = false;
    let mountedBundle: FincodeUiBundle | null = null;
    (async () => {
      try {
        const bundle = await initFincodeUi();
        if (cancelled) return;
        fincodeRef.current = bundle;
        mountedBundle = bundle;
        mountFincodeUi(bundle.ui, FINCODE_MOUNT_ID);
        setCardFormLoading(false);
      } catch (e) {
        if (!cancelled) {
          setError(e as Error);
          setCardFormLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
      setCardFormLoading(false);
      unmountFincodeUi(mountedBundle?.ui);
      fincodeRef.current = null;
    };
  }, [showCardForm]);

  async function subscribe(planId: string) {
    const isFree = planId === FREE_PLAN_ID;
    if (!isFree && !selectedCardId) {
      setError(new Error("カードを選択してください。"));
      return;
    }
    setError(null);
    setSubmittingPlan(planId);
    try {
      await apiFetch("/api/subscription", {
        method: "POST",
        body: JSON.stringify({
          fincode_plan_id: planId,
          ...(isFree ? {} : { card_id: selectedCardId })
        })
      });
      const wasOnPageOne = page === 1;
      setPage(1);
      const tasks: Promise<unknown>[] = [refreshSubscription()];
      if (wasOnPageOne) tasks.push(refreshHistory(1));
      await Promise.all(tasks);
      window.location.hash = "subscription";
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setSubmittingPlan(null);
    }
  }

  async function onCancel() {
    if (!sub) return;
    if (!confirm("本当に解約しますか？")) return;
    setCancelling(true);
    setError(null);
    try {
      const updated = await apiFetch<Subscription>("/api/subscription", { method: "DELETE" });
      setSub(updated);
      const wasOnPageOne = page === 1;
      setPage(1);
      if (wasOnPageOne) await refreshHistory(1);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setCancelling(false);
    }
  }

  async function onSubmitCard(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCardSubmitting(true);
    try {
      const bundle = fincodeRef.current;
      if (!bundle) throw new Error("fincode UI コンポーネントが初期化されていません。");
      const token = await tokenizeViaUi(bundle.fincode, bundle.ui);
      if (!token) {
        throw new Error("カードトークンの取得に失敗しました。");
      }
      await apiFetch("/api/subscription/cards", {
        method: "POST",
        body: JSON.stringify({ token })
      });
      await refreshPlansAndCards();
      setShowCardForm(false);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setCardSubmitting(false);
    }
  }

  async function onDeleteCard(cardId: number) {
    if (deletingCardId !== null) return;
    if (!confirm("このカードを削除しますか？")) return;
    setError(null);
    setDeletingCardId(cardId);
    try {
      await apiFetch(`/api/subscription/cards/${cardId}`, { method: "DELETE" });
      await refreshPlansAndCards();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setDeletingCardId(null);
    }
  }

  const totalPages = history ? Math.max(1, Math.ceil(history.total / history.per_page)) : 1;
  const selectedCard = cards.find((c) => c.id === selectedCardId) ?? cards[0] ?? null;

  return (
    <section className={pageClass}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-1 text-xs font-bold uppercase text-sky-700">Dashboard</p>
          <h1 className="text-3xl font-bold text-sky-950">ようこそ、{user?.name} さん</h1>
        </div>
      </div>

      <ErrorBanner error={error} />

      <div className="grid gap-3 md:grid-cols-3">
        <article className={summaryCardClass}>
          <span className="text-sm text-slate-500">現在の契約</span>
          <strong className="text-2xl font-bold leading-tight text-sky-950">
            {!subscriptionLoaded ? "読み込み中..." : sub ? sub.plan_name : "未登録"}
          </strong>
          <small className="text-sm text-slate-500">
            {sub ? `${sub.status} / ${formatPlanPrice(sub.plan_amount, sub.plan_interval)}` : "プランを選択して契約できます"}
          </small>
        </article>
        <article className={summaryCardClass}>
          <span className="text-sm text-slate-500">登録カード</span>
          <strong className="text-2xl font-bold leading-tight text-sky-950">
            {plansLoaded ? `${cards.length} 枚` : "読み込み中..."}
          </strong>
          <small className="text-sm text-slate-500">
            {selectedCard ? `${selectedCard.brand} **** ${selectedCard.last4}` : "支払いカードを追加できます"}
          </small>
        </article>
        <article className={summaryCardClass}>
          <span className="text-sm text-slate-500">直近決済</span>
          <strong className="text-2xl font-bold leading-tight text-sky-950">
            {latestHistory ? `¥${latestHistory.amount.toLocaleString()}` : "履歴なし"}
          </strong>
          <small className="text-sm text-slate-500">
            {latestHistory ? new Date(latestHistory.charged_at).toLocaleString("ja-JP") : "決済後に表示されます"}
          </small>
        </article>
      </div>

      <section id="subscription" className={sectionClass}>
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-bold text-sky-950">契約</h2>
        </div>
        {!subscriptionLoaded ? (
          <p className="text-slate-600">読み込み中...</p>
        ) : !sub ? (
          <article className={cardClass}>
            <p className="text-slate-700">アクティブな契約はありません。</p>
            <p className="mt-4">
              <a href="#plans" className={primaryLinkClass}>
                プランを選ぶ
              </a>
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
                <dd className="mt-1 font-semibold text-slate-900">{formatPlanPrice(sub.plan_amount, sub.plan_interval)}</dd>
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
                <LoadingButton type="button" variant="danger" isLoading={cancelling} loadingLabel="解約中..." onClick={onCancel}>
                  解約する
                </LoadingButton>
              </p>
            )}
          </article>
        )}
      </section>

      <section id="plans" className={sectionClass}>
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-bold text-sky-950">プラン</h2>
        </div>
        {!plansLoaded ? (
          <p className="text-slate-600">読み込み中...</p>
        ) : (
          <>
            {cards.length === 0 ? (
              <article className={cardClass}>
                <p className="text-slate-700">有料プランの契約にはカードが必要です。フリープランはカード無しで契約できます。</p>
                <p className="mt-4">
                  <a href="#cards" className={primaryLinkClass}>
                    カードを登録する
                  </a>
                </p>
              </article>
            ) : (
              <label className={labelClass}>
                <span>支払いカード</span>
                <select
                  className={inputClass}
                  value={selectedCardId ?? ""}
                  onChange={(e) => setSelectedCardId(Number(e.target.value))}
                >
                  {cards.map((card) => (
                    <option key={card.id} value={card.id}>
                      {card.brand} **** {card.last4} ({card.exp_month}/{card.exp_year})
                    </option>
                  ))}
                </select>
              </label>
            )}
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {plans.map((plan) => (
                <li key={plan.fincode_plan_id} className={`${cardClass} grid content-start gap-2`}>
                  <h3 className="text-lg font-bold text-sky-950">{plan.name}</h3>
                  <p className="text-2xl font-bold text-slate-900">
                    {plan.amount === 0 ? (
                      "無料"
                    ) : (
                      <>
                        ¥{plan.amount.toLocaleString()} <span className="text-base font-normal text-slate-500">/ {plan.interval}</span>
                      </>
                    )}
                  </p>
                  <LoadingButton
                    type="button"
                    disabled={(plan.amount > 0 && cards.length === 0) || submittingPlan !== null}
                    isLoading={submittingPlan === plan.fincode_plan_id}
                    loadingLabel="登録中..."
                    title={plan.amount > 0 && cards.length === 0 ? "先にカードを登録してください" : undefined}
                    onClick={() => subscribe(plan.fincode_plan_id)}
                  >
                    このプランを契約
                  </LoadingButton>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section id="cards" className={sectionClass}>
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl font-bold text-sky-950">カード</h2>
          {!showCardForm && (
            <button
              type="button"
              className={primaryLinkClass}
              onClick={() => {
                setError(null);
                setShowCardForm(true);
                setCardFormLoading(true);
              }}
            >
              カードを追加
            </button>
          )}
        </div>
        <article className={cardClass}>
          <h3 className="mb-3 text-lg font-bold text-sky-950">登録済みカード</h3>
          {!plansLoaded ? (
            <p className="text-slate-600">読み込み中...</p>
          ) : cards.length === 0 ? (
            <p className="text-slate-700">登録済みのカードはまだありません。</p>
          ) : (
            <ul className="grid gap-3">
              {cards.map((card) => (
                <li key={card.id} className="flex items-center justify-between gap-3 bg-sky-50 px-4 py-3">
                  <span className="text-sm font-medium text-slate-800">
                    {card.brand} **** {card.last4} ({card.exp_month}/{card.exp_year})
                  </span>
                  <LoadingButton
                    type="button"
                    variant="ghost"
                    className="min-h-0 text-red-700 hover:text-red-900 focus:ring-red-500"
                    disabled={deletingCardId !== null}
                    isLoading={deletingCardId === card.id}
                    loadingLabel="削除中..."
                    onClick={() => onDeleteCard(card.id)}
                  >
                    削除
                  </LoadingButton>
                </li>
              ))}
            </ul>
          )}
        </article>
        {showCardForm && (
          <article className={`${cardClass} max-w-[480px]`}>
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-lg font-bold text-sky-950">新規カードを追加</h3>
              <button
                type="button"
                className="text-sm font-semibold text-slate-600 transition-colors hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
                onClick={() => setShowCardForm(false)}
                disabled={cardSubmitting}
              >
                閉じる
              </button>
            </div>
            <p className="mt-2 text-sm text-slate-600">
              カード番号と CVC はサーバーへ送信されません。fincode の UI コンポーネントでトークン化されたトークンのみがバックエンドへ送信されます。
            </p>
            <form onSubmit={onSubmitCard} className="relative mt-3 grid gap-3">
              {cardFormLoading && (
                <div
                  className="absolute inset-0 z-10 flex items-center justify-center bg-slate-900/50"
                  role="status"
                  aria-live="polite"
                  aria-label="カード入力フォームを読み込み中"
                >
                  <span
                    aria-hidden="true"
                    className="h-8 w-8 animate-spin border-2 border-white border-t-transparent"
                  />
                </div>
              )}
              <div id={`${FINCODE_MOUNT_ID}-form`} className="max-w-full">
                <div id={FINCODE_MOUNT_ID} className="min-h-96 border border-sky-200 bg-white p-3" />
              </div>
              <LoadingButton type="submit" isLoading={cardSubmitting} loadingLabel="登録中...">
                カードを追加
              </LoadingButton>
            </form>
          </article>
        )}
      </section>

      <section id="history" className={sectionClass}>
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-bold text-sky-950">履歴</h2>
        </div>
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
                {history.data.map((record) => (
                  <tr key={record.id}>
                    <td className="border-b border-sky-100 px-4 py-3 text-sm text-slate-800">
                      {new Date(record.charged_at).toLocaleString("ja-JP")}
                    </td>
                    <td className="border-b border-sky-100 px-4 py-3 text-sm text-slate-800">{record.status}</td>
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
    </section>
  );
}
