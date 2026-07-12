import { LoadingButton } from "../../components/LoadingButton";
import { FREE_PLAN_ID } from "../../lib/constants";
import { formatCardLabelWithExpiry } from "../../lib/format";
import { inputClass, labelClass, primaryLinkClass, sectionClass } from "../../lib/styles";
import type { Subscription, Plan, Card } from "../../types/api";
import { cardClass } from "./styles";

type PlanSectionProps = {
  plansLoaded: boolean;
  plans: Plan[];
  cards: Card[];
  sub: Subscription;
  selectedCardId: number | null;
  onSelectCardId: (cardId: number) => void;
  submittingPlan: string | null;
  onSubscribe: (planId: string) => void;
  onChangePlan: (planId: string) => void;
};

export function PlanSection({
  plansLoaded,
  plans,
  cards,
  sub,
  selectedCardId,
  onSelectCardId,
  submittingPlan,
  onSubscribe,
  onChangePlan
}: PlanSectionProps) {
  return (
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
                onChange={(e) => onSelectCardId(Number(e.target.value))}
              >
                {cards.map((card) => (
                  <option key={card.id} value={card.id}>
                    {formatCardLabelWithExpiry(card)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {plans.map((plan) => {
              // unpaid も「現契約あり」として扱う。新規契約（POST）はバックエンドが
              // 409 (active_subscription_exists) で拒否するため、プラン変更（PATCH）に流す。
              const activeSub = sub && (sub.status === "active" || sub.status === "unpaid") ? sub : null;
              const isCurrentPlan = activeSub?.fincode_plan_id === plan.fincode_plan_id;
              const planChangeBlocked = activeSub?.cancel_at_period_end ?? false;
              const isFreeToPaid =
                activeSub?.fincode_plan_id === FREE_PLAN_ID && plan.fincode_plan_id !== FREE_PLAN_ID;
              const needsCard = plan.amount > 0 && (!activeSub || isFreeToPaid);
              const cardMissing = needsCard && cards.length === 0;
              const buttonLabel = isCurrentPlan
                ? "現在のプラン"
                : planChangeBlocked
                  ? "解約予約中"
                  : activeSub
                  ? "このプランに変更"
                  : "このプランを契約";
              return (
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
                    disabled={isCurrentPlan || planChangeBlocked || cardMissing || submittingPlan !== null}
                    isLoading={submittingPlan === plan.fincode_plan_id}
                    loadingLabel={activeSub ? "変更中..." : "登録中..."}
                    title={
                      planChangeBlocked
                        ? "解約予約中はプラン変更できません"
                        : cardMissing
                          ? "先にカードを登録してください"
                          : undefined
                    }
                    onClick={() =>
                      activeSub ? onChangePlan(plan.fincode_plan_id) : onSubscribe(plan.fincode_plan_id)
                    }
                  >
                    {buttonLabel}
                  </LoadingButton>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
