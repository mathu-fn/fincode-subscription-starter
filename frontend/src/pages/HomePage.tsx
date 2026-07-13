import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { ConfirmDialog } from "../components/ConfirmDialog";
import { ErrorBanner } from "../components/ErrorBanner";
import { Label } from "../components/Label";
import { StatusBadge } from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { apiFetch, ApiError } from "../lib/apiClient";
import { FincodeUiBundle, initFincodeUi, mountFincodeUi, tokenizeViaUi, unmountFincodeUi } from "../lib/fincodeJs";
import { isFincodeMockMode } from "../lib/fincodeMode";
import { pageClass } from "../lib/styles";
import type { Subscription, Plan, Card, HistoryItem, PaginatedBillingHistory } from "../types/api";

import { CardsSection } from "./home/CardsSection";
import { HistorySection } from "./home/HistorySection";
import { PlansSection } from "./home/PlansSection";
import { SubscriptionSection } from "./home/SubscriptionSection";
import { SummaryCard } from "./home/SummaryCard";
import {
  cancelDialogDescription,
  FINCODE_MOUNT_ID,
  formatDateTime,
  formatPlanPrice,
  formatYen,
  FREE_PLAN_ID,
  PER_PAGE
} from "./home/utils";

export function HomePage() {
  const mockMode = isFincodeMockMode();
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
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [cardPendingDelete, setCardPendingDelete] = useState<Card | null>(null);
  const [showCardForm, setShowCardForm] = useState(false);
  const [cardFormLoading, setCardFormLoading] = useState(false);
  const [mockToken, setMockToken] = useState("tok_mock_visa");
  const [page, setPage] = useState(1);
  const [history, setHistory] = useState<PaginatedBillingHistory | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
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
    } finally {
      setHistoryLoaded(true);
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
    // モックモードでは fincode.js を読み込まず、テストトークンを直接入力する。
    if (!showCardForm || mockMode) return;
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
  }, [showCardForm, mockMode]);

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

  async function changePlan(planId: string) {
    if (!sub) return;
    const isFree = planId === FREE_PLAN_ID;
    const isFreeToPaid = sub.fincode_plan_id === FREE_PLAN_ID && !isFree;
    if (isFreeToPaid && !selectedCardId) {
      setError(new Error("カードを選択してください。"));
      return;
    }
    setError(null);
    setSubmittingPlan(planId);
    try {
      const updated = await apiFetch<Subscription>("/api/subscription", {
        method: "PATCH",
        body: JSON.stringify({
          fincode_plan_id: planId,
          ...(isFreeToPaid ? { card_id: selectedCardId } : {})
        })
      });
      setSub(updated);
      const wasOnPageOne = page === 1;
      setPage(1);
      if (wasOnPageOne) await refreshHistory(1);
      window.location.hash = "subscription";
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setSubmittingPlan(null);
    }
  }

  async function confirmCancel() {
    if (!sub) return;
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
      setShowCancelConfirm(false);
    }
  }

  async function onSubmitCard(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setCardSubmitting(true);
    try {
      let token: string;
      if (mockMode) {
        token = mockToken.trim();
        if (!token) throw new Error("テストトークンを入力してください。");
      } else {
        const bundle = fincodeRef.current;
        if (!bundle) throw new Error("fincode UI コンポーネントが初期化されていません。");
        // トークンが取れなかった場合は tokenizeViaUi 自身が throw する。
        token = await tokenizeViaUi(bundle.fincode, bundle.ui);
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

  async function confirmDeleteCard() {
    if (!cardPendingDelete) return;
    const cardId = cardPendingDelete.id;
    setError(null);
    setDeletingCardId(cardId);
    try {
      await apiFetch(`/api/subscription/cards/${cardId}`, { method: "DELETE" });
      await refreshPlansAndCards();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setDeletingCardId(null);
      setCardPendingDelete(null);
    }
  }

  const totalPages = history ? Math.max(1, Math.ceil(history.total / history.per_page)) : 1;
  const selectedCard = cards.find((c) => c.id === selectedCardId) ?? cards[0] ?? null;

  return (
    <section className={pageClass}>
      <div>
        <Label>Dashboard</Label>
        <h1 className="mt-1 font-dot text-3xl tracking-tight text-black sm:text-4xl">
          ようこそ、{user?.name} さん
        </h1>
      </div>

      <ErrorBanner error={error} />

      <div className="grid gap-3 md:grid-cols-3">
        <SummaryCard label="現在の契約" loading={!subscriptionLoaded}>
          <strong className="text-2xl font-bold leading-tight text-black">
            {sub ? sub.plan_name : "未登録"}
          </strong>
          <small className="flex flex-wrap items-center gap-2 text-sm text-muted">
            {sub ? (
              <>
                <StatusBadge status={sub.status} />
                <span className="font-mono">{formatPlanPrice(sub.plan_amount, sub.plan_interval)}</span>
                {sub.cancel_at_period_end && <span>解約予約中</span>}
              </>
            ) : (
              "プランを選択して契約できます"
            )}
          </small>
        </SummaryCard>
        <SummaryCard label="登録カード" loading={!plansLoaded}>
          <strong className="font-mono text-2xl font-semibold leading-tight text-black">
            {cards.length} 枚
          </strong>
          <small className="text-sm text-muted">
            {selectedCard ? `${selectedCard.brand} **** ${selectedCard.last4}` : "支払いカードを追加できます"}
          </small>
        </SummaryCard>
        <SummaryCard label="直近決済" loading={!historyLoaded}>
          <strong className="font-mono text-2xl font-semibold leading-tight text-black">
            {latestHistory ? formatYen(latestHistory.amount) : "履歴なし"}
          </strong>
          <small className="text-sm text-muted">
            {latestHistory ? formatDateTime(latestHistory.charged_at) : "決済後に表示されます"}
          </small>
        </SummaryCard>
      </div>

      <SubscriptionSection
        subscriptionLoaded={subscriptionLoaded}
        sub={sub}
        cancelling={cancelling}
        onRequestCancel={() => setShowCancelConfirm(true)}
      />

      <PlansSection
        plansLoaded={plansLoaded}
        plans={plans}
        cards={cards}
        selectedCardId={selectedCardId}
        onSelectCard={(id) => setSelectedCardId(id)}
        sub={sub}
        submittingPlan={submittingPlan}
        onSubscribe={subscribe}
        onChangePlan={changePlan}
      />

      <CardsSection
        plansLoaded={plansLoaded}
        cards={cards}
        mockMode={mockMode}
        showCardForm={showCardForm}
        cardFormLoading={cardFormLoading}
        cardSubmitting={cardSubmitting}
        mockToken={mockToken}
        deletingCardId={deletingCardId}
        onAddCardClick={() => {
          setError(null);
          setShowCardForm(true);
          // モックモードは fincode.js を初期化しないのでローディング表示も不要。
          setCardFormLoading(!mockMode);
        }}
        onCloseCardForm={() => setShowCardForm(false)}
        onMockTokenChange={(value) => setMockToken(value)}
        onSubmitCard={onSubmitCard}
        onRequestDeleteCard={(card) => setCardPendingDelete(card)}
      />

      <HistorySection
        history={history}
        page={page}
        totalPages={totalPages}
        onPrevPage={() => setPage((current) => current - 1)}
        onNextPage={() => setPage((current) => current + 1)}
      />

      <ConfirmDialog
        open={showCancelConfirm}
        title="本当に解約しますか？"
        description={sub ? cancelDialogDescription(sub) : undefined}
        confirmLabel="解約する"
        loadingLabel="解約中..."
        variant="danger"
        isConfirming={cancelling}
        onConfirm={confirmCancel}
        onCancel={() => setShowCancelConfirm(false)}
      />
      <ConfirmDialog
        open={cardPendingDelete !== null}
        title="カードを削除しますか？"
        description={
          cardPendingDelete
            ? `${cardPendingDelete.brand} **** ${cardPendingDelete.last4} を削除します。`
            : undefined
        }
        confirmLabel="削除"
        loadingLabel="削除中..."
        variant="danger"
        isConfirming={deletingCardId !== null}
        onConfirm={confirmDeleteCard}
        onCancel={() => setCardPendingDelete(null)}
      />
    </section>
  );
}
