import type { FormEvent } from "react";

import { Card } from "../../components/Card";
import { FormField } from "../../components/FormField";
import { Input } from "../../components/Input";
import { LoadingButton } from "../../components/LoadingButton";
import { primaryLinkClass, sectionClass, sectionTitle } from "../../lib/styles";
import type { Card as CardType } from "../../types/api";

import { FINCODE_MOUNT_ID } from "./utils";

type CardsSectionProps = {
  plansLoaded: boolean;
  cards: CardType[];
  mockMode: boolean;
  showCardForm: boolean;
  cardFormLoading: boolean;
  cardSubmitting: boolean;
  mockToken: string;
  deletingCardId: number | null;
  onAddCardClick: () => void;
  onCloseCardForm: () => void;
  onMockTokenChange: (value: string) => void;
  onSubmitCard: (e: FormEvent) => void;
  onRequestDeleteCard: (card: CardType) => void;
};

export function CardsSection({
  plansLoaded,
  cards,
  mockMode,
  showCardForm,
  cardFormLoading,
  cardSubmitting,
  mockToken,
  deletingCardId,
  onAddCardClick,
  onCloseCardForm,
  onMockTokenChange,
  onSubmitCard,
  onRequestDeleteCard
}: CardsSectionProps) {
  return (
    <section id="cards" className={sectionClass}>
      <div className="flex items-center justify-between gap-3">
        <h2 className={sectionTitle}>カード</h2>
        {!showCardForm && (
          <button type="button" className={primaryLinkClass} onClick={onAddCardClick}>
            カードを追加
          </button>
        )}
      </div>
      <Card className="p-4">
        <h3 className="mb-3 text-lg font-bold text-black">登録済みカード</h3>
        {!plansLoaded ? (
          <p className="text-sm text-muted">読み込み中...</p>
        ) : cards.length === 0 ? (
          <p className="text-muted">登録済みのカードはまだありません。</p>
        ) : (
          <ul className="border-t border-line">
            {cards.map((card) => (
              <li
                key={card.id}
                className="flex items-center justify-between gap-3 border-b border-line py-3"
              >
                <span className="font-mono text-sm text-black">
                  {card.brand} **** {card.last4} ({card.exp_month}/{card.exp_year})
                </span>
                <LoadingButton
                  type="button"
                  variant="ghost"
                  className="min-h-0"
                  disabled={deletingCardId !== null}
                  isLoading={deletingCardId === card.id}
                  loadingLabel="削除中..."
                  onClick={() => onRequestDeleteCard(card)}
                >
                  削除
                </LoadingButton>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {showCardForm && (
        <Card className="max-w-[480px] p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-lg font-bold text-black">新規カードを追加</h3>
            <button
              type="button"
              className="font-mono text-xs uppercase tracking-[0.1em] text-muted transition-colors duration-150 hover:text-black disabled:cursor-not-allowed disabled:opacity-50"
              onClick={onCloseCardForm}
              disabled={cardSubmitting}
            >
              閉じる
            </button>
          </div>
          <p className="mt-2 text-sm text-muted">
            {mockMode
              ? "モックモードです。fincode は呼び出されません。任意のテストトークンを直接入力すると、ダミーのカードが登録されます。"
              : "カード番号と CVC はサーバーへ送信されません。fincode の UI コンポーネントでトークン化されたトークンのみがバックエンドへ送信されます。"}
          </p>
          <form onSubmit={onSubmitCard} className="relative mt-3 grid gap-3">
            {cardFormLoading && (
              <div
                className="absolute inset-0 z-10 flex items-center justify-center bg-black/50"
                role="status"
                aria-live="polite"
                aria-label="カード入力フォームを読み込み中"
              >
                <span className="text-sm font-semibold text-white">読み込み中...</span>
              </div>
            )}
            {mockMode ? (
              <FormField label="テストトークンを直接入力">
                <Input
                  value={mockToken}
                  onChange={(e) => onMockTokenChange(e.target.value)}
                  placeholder="tok_mock_visa"
                  autoComplete="off"
                />
              </FormField>
            ) : (
              <div id={`${FINCODE_MOUNT_ID}-form`} className="max-w-full">
                <div id={FINCODE_MOUNT_ID} className="min-h-96 border border-line bg-white p-3" />
              </div>
            )}
            <LoadingButton type="submit" isLoading={cardSubmitting} loadingLabel="登録中...">
              カードを追加
            </LoadingButton>
          </form>
        </Card>
      )}
    </section>
  );
}
