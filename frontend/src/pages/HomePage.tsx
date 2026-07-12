import { useEffect } from "react";
import { useLocation } from "react-router-dom";

import { ConfirmDialog } from "../components/ConfirmDialog";
import { ErrorBanner } from "../components/ErrorBanner";
import { useAuth } from "../hooks/useAuth";
import { useSubscriptionDashboard } from "../hooks/useSubscriptionDashboard";
import { formatCardLabel, formatDateTime } from "../lib/format";
import { pageClass } from "../lib/styles";
import type { Subscription } from "../types/api";
import { BillingHistorySection } from "./home/BillingHistorySection";
import { CardSection } from "./home/CardSection";
import { PlanSection } from "./home/PlanSection";
import { SubscriptionSection } from "./home/SubscriptionSection";
import { SummaryCards } from "./home/SummaryCards";

function cancelDialogDescription(sub: NonNullable<Subscription>): string {
  if (sub.fincode_subscription_id && sub.current_period_end) {
    return `現在の契約は ${formatDateTime(sub.current_period_end)} まで利用できます。次回以降の請求は発生しません。`;
  }
  return "現在の契約はただちに解約されます。解約後は利用できません。";
}

export function HomePage() {
  const { user } = useAuth();
  const location = useLocation();
  const dashboard = useSubscriptionDashboard();

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

  return (
    <section className={pageClass}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-1 text-xs font-bold uppercase text-sky-700">Dashboard</p>
          <h1 className="text-3xl font-bold text-sky-950">ようこそ、{user?.name} さん</h1>
        </div>
      </div>

      <ErrorBanner error={dashboard.error} />

      <SummaryCards
        subscriptionLoaded={dashboard.subscriptionLoaded}
        sub={dashboard.sub}
        plansLoaded={dashboard.plansLoaded}
        cards={dashboard.cards}
        selectedCard={dashboard.selectedCard}
        historyLoaded={dashboard.historyLoaded}
        latestHistory={dashboard.latestHistory}
      />

      <SubscriptionSection
        subscriptionLoaded={dashboard.subscriptionLoaded}
        sub={dashboard.sub}
        cancelling={dashboard.cancelling}
        onRequestCancel={() => dashboard.setShowCancelConfirm(true)}
      />

      <PlanSection
        plansLoaded={dashboard.plansLoaded}
        plans={dashboard.plans}
        cards={dashboard.cards}
        sub={dashboard.sub}
        selectedCardId={dashboard.selectedCardId}
        onSelectCardId={dashboard.setSelectedCardId}
        submittingPlan={dashboard.submittingPlan}
        onSubscribe={dashboard.subscribe}
        onChangePlan={dashboard.changePlan}
      />

      <CardSection
        mockMode={dashboard.mockMode}
        plansLoaded={dashboard.plansLoaded}
        cards={dashboard.cards}
        deletingCardId={dashboard.deletingCardId}
        onRequestDelete={dashboard.setCardPendingDelete}
        showCardForm={dashboard.showCardForm}
        onOpenCardForm={dashboard.openCardForm}
        onCloseCardForm={dashboard.closeCardForm}
        cardFormLoading={dashboard.cardFormLoading}
        cardSubmitting={dashboard.cardSubmitting}
        mockToken={dashboard.mockToken}
        onChangeMockToken={dashboard.setMockToken}
        onSubmitCard={dashboard.onSubmitCard}
      />

      <BillingHistorySection
        history={dashboard.history}
        page={dashboard.page}
        totalPages={dashboard.totalPages}
        setPage={dashboard.setPage}
      />

      <ConfirmDialog
        open={dashboard.showCancelConfirm}
        title="本当に解約しますか？"
        description={dashboard.sub ? cancelDialogDescription(dashboard.sub) : undefined}
        confirmLabel="解約する"
        loadingLabel="解約中..."
        variant="danger"
        isConfirming={dashboard.cancelling}
        onConfirm={dashboard.confirmCancel}
        onCancel={() => dashboard.setShowCancelConfirm(false)}
      />
      <ConfirmDialog
        open={dashboard.cardPendingDelete !== null}
        title="カードを削除しますか？"
        description={
          dashboard.cardPendingDelete
            ? `${formatCardLabel(dashboard.cardPendingDelete)} を削除します。`
            : undefined
        }
        confirmLabel="削除"
        loadingLabel="削除中..."
        variant="danger"
        isConfirming={dashboard.deletingCardId !== null}
        onConfirm={dashboard.confirmDeleteCard}
        onCancel={() => dashboard.setCardPendingDelete(null)}
      />
    </section>
  );
}
