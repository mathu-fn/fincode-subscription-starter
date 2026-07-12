import type { FormEvent } from "react";

import { LoadingButton } from "../../components/LoadingButton";
import { FINCODE_MOUNT_ID } from "../../lib/constants";
import { formatCardLabelWithExpiry } from "../../lib/format";
import { inputClass, labelClass, primaryLinkClass, sectionClass } from "../../lib/styles";
import type { Card } from "../../types/api";
import { cardClass } from "./styles";

type CardSectionProps = {
  mockMode: boolean;
  plansLoaded: boolean;
  cards: Card[];
  deletingCardId: number | null;
  onRequestDelete: (card: Card) => void;
  showCardForm: boolean;
  onOpenCardForm: () => void;
  onCloseCardForm: () => void;
  cardFormLoading: boolean;
  cardSubmitting: boolean;
  mockToken: string;
  onChangeMockToken: (value: string) => void;
  onSubmitCard: (e: FormEvent) => void;
};

export function CardSection({
  mockMode,
  plansLoaded,
  cards,
  deletingCardId,
  onRequestDelete,
  showCardForm,
  onOpenCardForm,
  onCloseCardForm,
  cardFormLoading,
  cardSubmitting,
  mockToken,
  onChangeMockToken,
  onSubmitCard
}: CardSectionProps) {
  return (
    <section id="cards" className={sectionClass}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-bold text-sky-950">カード</h2>
        {!showCardForm && (
          <button type="button" className={primaryLinkClass} onClick={onOpenCardForm}>
            カードを追加
          </button>
        )}
      </div>
      <article className={cardClass}>
        <h3 className="mb-3 text-lg font-bold text-sky-950">登録済みカード</h3>
        {!plansLoaded ? (
          <p className="text-slate-600">読み込み中...</p>
        ) : cards.length === 0 ? (
          <p className="text-slate-700">登録済みのカードはまだありません。</p>
        ) : (
          <ul className="grid gap-3">
            {cards.map((card) => (
              <li key={card.id} className="flex items-center justify-between gap-3 bg-sky-50 px-4 py-3">
                <span className="text-sm font-medium text-slate-800">
                  {formatCardLabelWithExpiry(card)}
                </span>
                <LoadingButton
                  type="button"
                  variant="ghost"
                  className="min-h-0 text-red-700 hover:text-red-900 focus:ring-red-500"
                  disabled={deletingCardId !== null}
                  isLoading={deletingCardId === card.id}
                  loadingLabel="削除中..."
                  onClick={() => onRequestDelete(card)}
                >
                  削除
                </LoadingButton>
              </li>
            ))}
          </ul>
        )}
      </article>
      {showCardForm && (
        <article className={`${cardClass} max-w-[480px]`}>
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-lg font-bold text-sky-950">新規カードを追加</h3>
            <button
              type="button"
              className="text-sm font-semibold text-slate-600 transition-colors hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={onCloseCardForm}
              disabled={cardSubmitting}
            >
              閉じる
            </button>
          </div>
          <p className="mt-2 text-sm text-slate-600">
            {mockMode
              ? "モックモードです。fincode は呼び出されません。任意のテストトークンを直接入力すると、ダミーのカードが登録されます。"
              : "カード番号と CVC はサーバーへ送信されません。fincode の UI コンポーネントでトークン化されたトークンのみがバックエンドへ送信されます。"}
          </p>
          <form onSubmit={onSubmitCard} className="relative mt-3 grid gap-3">
            {cardFormLoading && (
              <div
                className="absolute inset-0 z-10 flex items-center justify-center bg-slate-900/50"
                role="status"
                aria-live="polite"
                aria-label="カード入力フォームを読み込み中"
              >
                <span
                  aria-hidden="true"
                  className="h-8 w-8 animate-spin border-2 border-white border-t-transparent"
                />
              </div>
            )}
            {mockMode ? (
              <label className={labelClass}>
                <span>テストトークンを直接入力</span>
                <input
                  className={inputClass}
                  value={mockToken}
                  onChange={(e) => onChangeMockToken(e.target.value)}
                  placeholder="tok_mock_visa"
                  autoComplete="off"
                />
              </label>
            ) : (
              <div id={`${FINCODE_MOUNT_ID}-form`} className="max-w-full">
                <div id={FINCODE_MOUNT_ID} className="min-h-96 border border-sky-200 bg-white p-3" />
              </div>
            )}
            <LoadingButton type="submit" isLoading={cardSubmitting} loadingLabel="登録中...">
              カードを追加
            </LoadingButton>
          </form>
        </article>
      )}
    </section>
  );
}
