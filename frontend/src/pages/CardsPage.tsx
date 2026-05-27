import { useEffect, useRef, useState } from "react";

import { ErrorBanner } from "../components/ErrorBanner";
import { apiFetch, ApiError } from "../lib/apiClient";
import { FincodeUiBundle, initFincodeUi, mountFincodeUi, tokenizeViaUi } from "../lib/fincodeJs";

type Card = {
  id: number;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  created_at: string;
};

const FINCODE_MOUNT_ID = "fincode-ui-mount";

export function CardsPage() {
  const [cards, setCards] = useState<Card[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const fincodeRef = useRef<FincodeUiBundle | null>(null);

  async function refresh() {
    try {
      const list = await apiFetch<Card[]>("/api/subscription/cards");
      setCards(list);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setLoaded(true);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const bundle = await initFincodeUi();
        if (cancelled) return;
        fincodeRef.current = bundle;
        mountFincodeUi(bundle.ui, FINCODE_MOUNT_ID);
      } catch (e) {
        if (!cancelled) setError(e as Error);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
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
      await refresh();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete(cardId: number) {
    setError(null);
    try {
      await apiFetch(`/api/subscription/cards/${cardId}`, { method: "DELETE" });
      await refresh();
    } catch (e) {
      setError(e as ApiError);
    }
  }

  return (
    <section className="page">
      <h1>カード管理</h1>
      <ErrorBanner error={error} />
      <article className="card">
        <h2>登録済みカード</h2>
        {!loaded ? (
          <p>読み込み中...</p>
        ) : cards.length === 0 ? (
          <p>登録済みのカードはまだありません。</p>
        ) : (
          <ul className="card-list">
            {cards.map((c) => (
              <li key={c.id}>
                <span>
                  {c.brand} **** {c.last4} ({c.exp_month}/{c.exp_year})
                </span>
                <button type="button" className="danger-link" onClick={() => onDelete(c.id)}>
                  削除
                </button>
              </li>
            ))}
          </ul>
        )}
      </article>
      <article className="card">
        <h2>新規カードを追加</h2>
        <p className="hint">
          カード番号と CVC はサーバーへ送信されません。fincode の UI コンポーネントでトークン化されたトークンのみがバックエンドへ送信されます。
        </p>
        <form onSubmit={onSubmit} className="form">
          <div id={`${FINCODE_MOUNT_ID}-form`} className="fincode-ui-frame">
            <div id={FINCODE_MOUNT_ID} className="fincode-ui-mount" />
          </div>
          <button type="submit" className="primary" disabled={submitting}>
            {submitting ? "登録中..." : "カードを追加"}
          </button>
        </form>
      </article>
    </section>
  );
}
