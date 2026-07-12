/**
 * HomePage（ダッシュボード）の状態と操作をまとめたカスタムフック。
 *
 * - 契約 / プラン / カード / 決済履歴の取得
 * - 契約・プラン変更・解約・カード追加/削除の各操作
 * - fincode UI コンポーネントのマウント（モックモードでは読み込まない）
 *
 * location.hash によるスクロールなど DOM 副作用は HomePage 側に残している。
 */

import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch, ApiError } from "../lib/apiClient";
import { FINCODE_MOUNT_ID, FREE_PLAN_ID } from "../lib/constants";
import { FincodeUiBundle, initFincodeUi, mountFincodeUi, tokenizeViaUi, unmountFincodeUi } from "../lib/fincodeJs";
import { isFincodeMockMode } from "../lib/fincodeMode";
import type { Subscription, Plan, Card, HistoryItem, PaginatedBillingHistory } from "../types/api";
import type { AppError } from "../types/ui";

const PER_PAGE = 10;

export function useSubscriptionDashboard() {
  const mockMode = isFincodeMockMode();
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
  const [error, setError] = useState<AppError>(null);
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

  // 各操作共通の「エラーをクリアして実行し、失敗は error 状態へ、最後に後始末」。
  async function runAction(task: () => Promise<void>, finish: () => void): Promise<void> {
    setError(null);
    try {
      await task();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      finish();
    }
  }

  async function subscribe(planId: string) {
    const isFree = planId === FREE_PLAN_ID;
    if (!isFree && !selectedCardId) {
      setError(new Error("カードを選択してください。"));
      return;
    }
    setSubmittingPlan(planId);
    await runAction(
      async () => {
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
      },
      () => setSubmittingPlan(null)
    );
  }

  async function changePlan(planId: string) {
    if (!sub) return;
    const isFree = planId === FREE_PLAN_ID;
    const isFreeToPaid = sub.fincode_plan_id === FREE_PLAN_ID && !isFree;
    if (isFreeToPaid && !selectedCardId) {
      setError(new Error("カードを選択してください。"));
      return;
    }
    setSubmittingPlan(planId);
    await runAction(
      async () => {
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
      },
      () => setSubmittingPlan(null)
    );
  }

  async function confirmCancel() {
    if (!sub) return;
    setCancelling(true);
    await runAction(
      async () => {
        const updated = await apiFetch<Subscription>("/api/subscription", { method: "DELETE" });
        setSub(updated);
        const wasOnPageOne = page === 1;
        setPage(1);
        if (wasOnPageOne) await refreshHistory(1);
      },
      () => {
        setCancelling(false);
        setShowCancelConfirm(false);
      }
    );
  }

  async function onSubmitCard(e: FormEvent) {
    e.preventDefault();
    setCardSubmitting(true);
    await runAction(
      async () => {
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
      },
      () => setCardSubmitting(false)
    );
  }

  async function confirmDeleteCard() {
    if (!cardPendingDelete) return;
    const cardId = cardPendingDelete.id;
    setDeletingCardId(cardId);
    await runAction(
      async () => {
        await apiFetch(`/api/subscription/cards/${cardId}`, { method: "DELETE" });
        await refreshPlansAndCards();
      },
      () => {
        setDeletingCardId(null);
        setCardPendingDelete(null);
      }
    );
  }

  function openCardForm() {
    setError(null);
    setShowCardForm(true);
    // モックモードは fincode.js を初期化しないのでローディング表示も不要。
    setCardFormLoading(!mockMode);
  }

  function closeCardForm() {
    setShowCardForm(false);
  }

  const totalPages = history ? Math.max(1, Math.ceil(history.total / history.per_page)) : 1;
  const selectedCard = cards.find((c) => c.id === selectedCardId) ?? cards[0] ?? null;

  return {
    mockMode,
    error,
    sub,
    subscriptionLoaded,
    plans,
    plansLoaded,
    cards,
    selectedCard,
    selectedCardId,
    setSelectedCardId,
    submittingPlan,
    cardSubmitting,
    cancelling,
    deletingCardId,
    showCancelConfirm,
    setShowCancelConfirm,
    cardPendingDelete,
    setCardPendingDelete,
    showCardForm,
    openCardForm,
    closeCardForm,
    cardFormLoading,
    mockToken,
    setMockToken,
    page,
    setPage,
    history,
    historyLoaded,
    latestHistory,
    totalPages,
    subscribe,
    changePlan,
    confirmCancel,
    onSubmitCard,
    confirmDeleteCard
  };
}
