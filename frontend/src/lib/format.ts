/**
 * 表示フォーマットの共有ヘルパー。
 *
 * 画面ごとに手組みされていた金額・日時・カードラベルの文字列生成を集約する。
 * 出力文字列は既存表示と完全一致させること（挙動を変えない）。
 */

import type { Card } from "../types/api";

export function formatPlanPrice(amount: number, interval: string): string {
  if (amount === 0) return "無料";
  return `¥${amount.toLocaleString()} / ${interval}`;
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("ja-JP");
}

/** 例: "VISA **** 4242" */
export function formatCardLabel(card: Pick<Card, "brand" | "last4">): string {
  return `${card.brand} **** ${card.last4}`;
}

/** 例: "VISA **** 4242 (12/2030)" */
export function formatCardLabelWithExpiry(
  card: Pick<Card, "brand" | "last4" | "exp_month" | "exp_year">
): string {
  return `${formatCardLabel(card)} (${card.exp_month}/${card.exp_year})`;
}
