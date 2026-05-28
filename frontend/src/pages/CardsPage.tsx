import { useEffect, useRef, useState } from "react";

import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingButton } from "../components/LoadingButton";
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
const pageClass = "mx-auto grid max-w-5xl gap-6";
const cardClass = "border border-sky-200 bg-white p-6 shadow-sm shadow-sky-100";

export function CardsPage() {
  const [cards, setCards] = useState<Card[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deletingCardId, setDeletingCardId] = useState<number | null>(null);
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
    setDeletingCardId(cardId);
    try {
      await apiFetch(`/api/subscription/cards/${cardId}`, { method: "DELETE" });
      await refresh();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setDeletingCardId(null);
    }
  }

  return (
    <section className={pageClass}>
      <h1 className="text-3xl font-bold text-sky-950">カード管理</h1>
      <ErrorBanner error={error} />
      <article className={cardClass}>
        <h2 className="mb-3 text-xl font-bold text-sky-950">登録済みカード</h2>
        {!loaded ? (
          <p className="text-slate-600">読み込み中...</p>
        ) : cards.length === 0 ? (
          <p className="text-slate-700">登録済みのカードはまだありません。</p>
        ) : (
          <ul className="grid gap-3">
            {cards.map((c) => (
              <li key={c.id} className="flex items-center justify-between gap-3 bg-sky-50 px-4 py-3">
                <span className="text-sm font-medium text-slate-800">
                  {c.brand} **** {c.last4} ({c.exp_month}/{c.exp_year})
                </span>
                <LoadingButton
                  type="button"
                  variant="ghost"
                  className="min-h-0 text-red-700 hover:text-red-900 focus:ring-red-500"
                  disabled={deletingCardId !== null}
                  isLoading={deletingCardId === c.id}
                  loadingLabel="削除中..."
                  onClick={() => onDelete(c.id)}
                >
                  削除
                </LoadingButton>
              </li>
            ))}
          </ul>
        )}
      </article>
      <article className={cardClass}>
        <h2 className="text-xl font-bold text-sky-950">新規カードを追加</h2>
        <p className="mt-3 text-sm text-slate-600">
          カード番号と CVC はサーバーへ送信されません。fincode の UI コンポーネントでトークン化されたトークンのみがバックエンドへ送信されます。
        </p>
        <form onSubmit={onSubmit} className="mt-4 grid gap-4">
          <div id={`${FINCODE_MOUNT_ID}-form`} className="max-w-full">
            <div id={FINCODE_MOUNT_ID} className="min-h-96 border border-sky-200 bg-white p-4" />
          </div>
          <LoadingButton type="submit" isLoading={submitting} loadingLabel="登録中...">
            カードを追加
          </LoadingButton>
        </form>
      </article>
    </section>
  );
}
