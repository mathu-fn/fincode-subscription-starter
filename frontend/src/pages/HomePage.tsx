import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
import { useAuth } from "../hooks/useAuth";
import { apiFetch, ApiError } from "../lib/apiClient";
import { FincodeUiBundle, initFincodeUi, mountFincodeUi, tokenizeViaUi, unmountFincodeUi } from "../lib/fincodeJs";

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

type Plan = {
  fincode_plan_id: string;
  name: string;
  amount: number;
  currency: string;
  interval: string;
};

type Card = {
  id: number;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  created_at: string;
};

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

const FINCODE_MOUNT_ID = "fincode-ui-mount";
const PER_PAGE = 10;

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
    let cancelled = false;
    let mountedBundle: FincodeUiBundle | null = null;
    (async () => {
      try {
        const bundle = await initFincodeUi();
        if (cancelled) return;
        fincodeRef.current = bundle;
        mountedBundle = bundle;
        mountFincodeUi(bundle.ui, FINCODE_MOUNT_ID);
      } catch (e) {
        if (!cancelled) setError(e as Error);
      }
    })();
    return () => {
      cancelled = true;
      unmountFincodeUi(mountedBundle?.ui);
      fincodeRef.current = null;
    };
  }, []);

  async function subscribe(planId: string) {
    if (!selectedCardId) {
      setError(new Error("カードを選択してください。"));
      return;
    }
    setError(null);
    setSubmittingPlan(planId);
    try {
      await apiFetch("/api/subscription", {
        method: "POST",
        body: JSON.stringify({ fincode_plan_id: planId, card_id: selectedCardId })
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
    <section className="page dashboard-page">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1>ようこそ、{user?.name} さん</h1>
        </div>
      </div>

      <ErrorBanner error={error} />

      <div className="summary-grid">
        <article className="summary-card">
          <span>現在の契約</span>
          <strong>{!subscriptionLoaded ? "読み込み中..." : sub ? sub.plan_name : "未登録"}</strong>
          <small>{sub ? `${sub.status} / ¥${sub.plan_amount.toLocaleString()} / ${sub.plan_interval}` : "プランを選択して契約できます"}</small>
        </article>
        <article className="summary-card">
          <span>登録カード</span>
          <strong>{plansLoaded ? `${cards.length} 枚` : "読み込み中..."}</strong>
          <small>{selectedCard ? `${selectedCard.brand} **** ${selectedCard.last4}` : "支払いカードを追加できます"}</small>
        </article>
        <article className="summary-card">
          <span>直近決済</span>
          <strong>{latestHistory ? `¥${latestHistory.amount.toLocaleString()}` : "履歴なし"}</strong>
          <small>{latestHistory ? new Date(latestHistory.charged_at).toLocaleString("ja-JP") : "決済後に表示されます"}</small>
        </article>
      </div>

      <section id="subscription" className="dashboard-section">
        <div className="section-heading">
          <h2>契約</h2>
        </div>
        {!subscriptionLoaded ? (
          <p>読み込み中...</p>
        ) : !sub ? (
          <article className="card">
            <p>アクティブな契約はありません。</p>
            <p className="actions">
              <a href="#plans" className="primary-link">
                プランを選ぶ
              </a>
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

      <section id="plans" className="dashboard-section">
        <div className="section-heading">
          <h2>プラン</h2>
        </div>
        {!plansLoaded ? (
          <p>読み込み中...</p>
        ) : (
          <>
            {cards.length === 0 ? (
              <article className="card">
                <p>契約にはカードが必要です。</p>
                <p className="actions">
                  <a href="#cards" className="primary-link">
                    カードを登録する
                  </a>
                </p>
              </article>
            ) : (
              <label className="field">
                <span>支払いカード</span>
                <select
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
            <ul className="plan-list">
              {plans.map((plan) => (
                <li key={plan.fincode_plan_id} className="card plan-card">
                  <h3>{plan.name}</h3>
                  <p className="price">
                    ¥{plan.amount.toLocaleString()} <span className="muted">/ {plan.interval}</span>
                  </p>
                  <button
                    type="button"
                    className="primary"
                    disabled={cards.length === 0 || submittingPlan !== null}
                    title={cards.length === 0 ? "先にカードを登録してください" : undefined}
                    onClick={() => subscribe(plan.fincode_plan_id)}
                  >
                    {submittingPlan === plan.fincode_plan_id ? "登録中..." : "このプランを契約"}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section id="cards" className="dashboard-section">
        <div className="section-heading">
          <h2>カード</h2>
        </div>
        <div className="dashboard-columns">
          <article className="card">
            <h3>登録済みカード</h3>
            {!plansLoaded ? (
              <p>読み込み中...</p>
            ) : cards.length === 0 ? (
              <p>登録済みのカードはまだありません。</p>
            ) : (
              <ul className="card-list">
                {cards.map((card) => (
                  <li key={card.id}>
                    <span>
                      {card.brand} **** {card.last4} ({card.exp_month}/{card.exp_year})
                    </span>
                    <button
                      type="button"
                      className="danger-link"
                      disabled={deletingCardId !== null}
                      onClick={() => onDeleteCard(card.id)}
                    >
                      {deletingCardId === card.id ? "削除中..." : "削除"}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </article>
          <article className="card">
            <h3>新規カードを追加</h3>
            <p className="hint">
              カード番号と CVC はサーバーへ送信されません。fincode の UI コンポーネントでトークン化されたトークンのみがバックエンドへ送信されます。
            </p>
            <form onSubmit={onSubmitCard} className="form">
              <div id={`${FINCODE_MOUNT_ID}-form`} className="fincode-ui-frame">
                <div id={FINCODE_MOUNT_ID} className="fincode-ui-mount" />
              </div>
              <button type="submit" className="primary" disabled={cardSubmitting}>
                {cardSubmitting ? "登録中..." : "カードを追加"}
              </button>
            </form>
          </article>
        </div>
      </section>

      <section id="history" className="dashboard-section">
        <div className="section-heading">
          <h2>履歴</h2>
        </div>
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
                {history.data.map((record) => (
                  <tr key={record.id}>
                    <td>{new Date(record.charged_at).toLocaleString("ja-JP")}</td>
                    <td>{record.status}</td>
                    <td>¥{record.amount.toLocaleString()}</td>
                    <td className="muted">{record.fincode_payment_id ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pagination">
              <button type="button" disabled={page === 1} onClick={() => setPage((current) => current - 1)}>
                前へ
              </button>
              <span>
                {history.page} / {totalPages}
              </span>
              <button
                type="button"
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
