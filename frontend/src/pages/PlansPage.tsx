import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
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
    <section className="page">
      <h1>プラン一覧</h1>
      <ErrorBanner error={error} />
      {!loaded ? (
        <p>読み込み中...</p>
      ) : (
        <>
          {cards.length === 0 ? (
            <article className="card">
              <p>契約にはカードが必要です。</p>
              <p className="actions">
                <Link to="/cards" className="primary-link">
                  カードを登録する
                </Link>
              </p>
            </article>
          ) : (
            <label className="field">
              <span>支払いカード</span>
              <select
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
          <ul className="plan-list">
            {plans.map((plan) => (
              <li key={plan.fincode_plan_id} className="card plan-card">
                <h2>{plan.name}</h2>
                <p className="price">
                  ¥{plan.amount.toLocaleString()} <span className="muted">/ {plan.interval}</span>
                </p>
                <button
                  type="button"
                  className="primary"
                  disabled={cards.length === 0 || submittingPlan === plan.fincode_plan_id}
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
  );
}
