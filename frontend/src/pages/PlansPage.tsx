import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingButton } from "../components/LoadingButton";
import { apiFetch, ApiError } from "../lib/apiClient";

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
};

const pageClass = "mx-auto grid max-w-5xl gap-6";
const cardClass = "border border-sky-200 bg-white p-6 shadow-sm shadow-sky-100";
const labelClass = "grid gap-1.5 text-sm font-semibold text-slate-700";
const inputClass =
  "min-h-11 border border-sky-200 bg-white px-3 py-2 text-base font-normal text-slate-900 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-200";
const primaryLinkClass =
  "inline-flex min-h-11 items-center justify-center border border-sky-600 bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2";

export function PlansPage() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [selectedCardId, setSelectedCardId] = useState<number | null>(null);
  const [submittingPlan, setSubmittingPlan] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Promise.all([apiFetch<Plan[]>("/api/subscription/plans"), apiFetch<Card[]>("/api/subscription/cards")])
      .then(([p, c]) => {
        setPlans(p);
        setCards(c);
        if (c.length > 0) setSelectedCardId(c[0].id);
      })
      .catch((e) => setError(e as ApiError))
      .finally(() => setLoaded(true));
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
      navigate("/subscription");
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setSubmittingPlan(null);
    }
  }

  return (
    <section className={pageClass}>
      <h1 className="text-3xl font-bold text-sky-950">プラン一覧</h1>
      <ErrorBanner error={error} />
      {!loaded ? (
        <p className="text-slate-600">読み込み中...</p>
      ) : (
        <>
          {cards.length === 0 ? (
            <article className={cardClass}>
              <p className="text-slate-700">契約にはカードが必要です。</p>
              <p className="mt-4">
                <Link to="/cards" className={primaryLinkClass}>
                  カードを登録する
                </Link>
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
                {cards.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.brand} **** {c.last4} ({c.exp_month}/{c.exp_year})
                  </option>
                ))}
              </select>
            </label>
          )}
          <ul className="grid gap-4">
            {plans.map((plan) => (
              <li key={plan.fincode_plan_id} className={`${cardClass} grid gap-3`}>
                <h2 className="text-xl font-bold text-sky-950">{plan.name}</h2>
                <p className="text-2xl font-bold text-slate-900">
                  ¥{plan.amount.toLocaleString()} <span className="text-base font-normal text-slate-500">/ {plan.interval}</span>
                </p>
                <LoadingButton
                  type="button"
                  disabled={cards.length === 0 || submittingPlan === plan.fincode_plan_id}
                  isLoading={submittingPlan === plan.fincode_plan_id}
                  loadingLabel="登録中..."
                  title={cards.length === 0 ? "先にカードを登録してください" : undefined}
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
  );
}
