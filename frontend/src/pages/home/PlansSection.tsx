import { Card } from "../../components/Card";
import { FormField } from "../../components/FormField";
import { LoadingButton } from "../../components/LoadingButton";
import { inputClass, primaryLinkClass, sectionClass, sectionTitle } from "../../lib/styles";
import type { Card as CardType, Plan, Subscription } from "../../types/api";

import { formatYen, FREE_PLAN_ID } from "./utils";

type PlansSectionProps = {
  plansLoaded: boolean;
  plans: Plan[];
  cards: CardType[];
  selectedCardId: number | null;
  onSelectCard: (id: number) => void;
  sub: Subscription;
  submittingPlan: string | null;
  onSubscribe: (planId: string) => void;
  onChangePlan: (planId: string) => void;
};

export function PlansSection({
  plansLoaded,
  plans,
  cards,
  selectedCardId,
  onSelectCard,
  sub,
  submittingPlan,
  onSubscribe,
  onChangePlan
}: PlansSectionProps) {
  return (
    <section id="plans" className={sectionClass}>
      <div className="flex items-center justify-between gap-4">
        <h2 className={sectionTitle}>プラン</h2>
      </div>
      {!plansLoaded ? (
        <p className="text-sm text-muted">読み込み中...</p>
      ) : (
        <>
          {cards.length === 0 ? (
            <Card className="p-4">
              <p className="text-muted">
                有料プランの契約にはカードが必要です。フリープランはカード無しで契約できます。
              </p>
              <p className="mt-4">
                <a href="#cards" className={primaryLinkClass}>
                  カードを登録する
                </a>
              </p>
            </Card>
          ) : (
            <FormField label="支払いカード" className="max-w-sm">
              <select
                className={inputClass}
                value={selectedCardId ?? ""}
                onChange={(e) => onSelectCard(Number(e.target.value))}
              >
                {cards.map((card) => (
                  <option key={card.id} value={card.id}>
                    {card.brand} **** {card.last4} ({card.exp_month}/{card.exp_year})
                  </option>
                ))}
              </select>
            </FormField>
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
                <li key={plan.fincode_plan_id}>
                  <Card className="grid h-full content-start gap-3 p-4">
                    <h3 className="text-lg font-bold text-black">{plan.name}</h3>
                    <p className="font-mono text-2xl text-black">
                      {plan.amount === 0 ? (
                        "無料"
                      ) : (
                        <>
                          {formatYen(plan.amount)}{" "}
                          <span className="text-base text-muted">/ {plan.interval}</span>
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
                  </Card>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
