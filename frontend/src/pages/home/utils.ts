// HomePage（ダッシュボード）で共有する定数と整形ヘルパ。
// セクションコンポーネント（home/*Section.tsx）と HomePage 本体の双方から参照する。
import type { Subscription } from "../../types/api";

// fincode UI コンポーネントのマウント先 DOM id。CardsSection が div を描画し、
// HomePage 側の初期化 effect が同じ id を mountFincodeUi に渡す。
export const FINCODE_MOUNT_ID = "fincode-ui-mount";

// 決済履歴の 1 ページあたり件数。
export const PER_PAGE = 10;

// 0円フリープランの番兵ID（バックエンドの FREE_PLAN_ID と一致）。
export const FREE_PLAN_ID = "free";

export function formatYen(amount: number): string {
  return `¥${amount.toLocaleString()}`;
}

export function formatPlanPrice(amount: number, interval: string): string {
  if (amount === 0) return "無料";
  return `${formatYen(amount)} / ${interval}`;
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("ja-JP");
}

export function cancelDialogDescription(sub: NonNullable<Subscription>): string {
  if (sub.fincode_subscription_id && sub.current_period_end) {
    return `現在の契約は ${formatDateTime(sub.current_period_end)} まで利用できます。次回以降の請求は発生しません。`;
  }
  return "現在の契約はただちに解約されます。解約後は利用できません。";
}
