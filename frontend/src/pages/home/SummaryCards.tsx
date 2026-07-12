import { Skeleton } from "../../components/Skeleton";
import { StatusBadge } from "../../components/StatusBadge";
import { formatCardLabel, formatDateTime, formatPlanPrice } from "../../lib/format";
import { summaryCardClass } from "../../lib/styles";
import type { Subscription, Card, HistoryItem } from "../../types/api";

type SummaryCardsProps = {
  subscriptionLoaded: boolean;
  sub: Subscription;
  plansLoaded: boolean;
  cards: Card[];
  selectedCard: Card | null;
  historyLoaded: boolean;
  latestHistory: HistoryItem | null;
};

export function SummaryCards({
  subscriptionLoaded,
  sub,
  plansLoaded,
  cards,
  selectedCard,
  historyLoaded,
  latestHistory
}: SummaryCardsProps) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <article className={summaryCardClass}>
        <span className="text-sm text-slate-500">現在の契約</span>
        {!subscriptionLoaded ? (
          <>
            <Skeleton className="mt-1 h-7 w-3/4" />
            <Skeleton className="mt-1 h-4 w-1/2" />
          </>
        ) : (
          <>
            <strong className="text-2xl font-bold leading-tight text-sky-950">
              {sub ? sub.plan_name : "未登録"}
            </strong>
            <small className="flex items-center gap-2 text-sm text-slate-500">
              {sub ? (
                <>
                  <StatusBadge status={sub.status} />
                  <span>{formatPlanPrice(sub.plan_amount, sub.plan_interval)}</span>
                  {sub.cancel_at_period_end && <span>解約予約中</span>}
                </>
              ) : (
                "プランを選択して契約できます"
              )}
            </small>
          </>
        )}
      </article>
      <article className={summaryCardClass}>
        <span className="text-sm text-slate-500">登録カード</span>
        {!plansLoaded ? (
          <>
            <Skeleton className="mt-1 h-7 w-1/2" />
            <Skeleton className="mt-1 h-4 w-3/4" />
          </>
        ) : (
          <>
            <strong className="text-2xl font-bold leading-tight text-sky-950">
              {cards.length} 枚
            </strong>
            <small className="text-sm text-slate-500">
              {selectedCard ? formatCardLabel(selectedCard) : "支払いカードを追加できます"}
            </small>
          </>
        )}
      </article>
      <article className={summaryCardClass}>
        <span className="text-sm text-slate-500">直近決済</span>
        {!historyLoaded ? (
          <>
            <Skeleton className="mt-1 h-7 w-1/2" />
            <Skeleton className="mt-1 h-4 w-3/4" />
          </>
        ) : (
          <>
            <strong className="text-2xl font-bold leading-tight text-sky-950">
              {latestHistory ? `¥${latestHistory.amount.toLocaleString()}` : "履歴なし"}
            </strong>
            <small className="text-sm text-slate-500">
              {latestHistory ? formatDateTime(latestHistory.charged_at) : "決済後に表示されます"}
            </small>
          </>
        )}
      </article>
    </div>
  );
}
