/**
 * テスト用フィクスチャビルダー。
 *
 * 既存テストに散らばっていたレスポンスオブジェクトを吸収する。
 * デフォルト値は既存テストで最頻出の「ベーシックプラン契約」に合わせている。
 */

import type { Card, HistoryItem, PaginatedBillingHistory, Plan, Subscription } from "../types/api";

type SubscriptionRecord = NonNullable<Subscription>;

export function buildSubscription(overrides: Partial<SubscriptionRecord> = {}): SubscriptionRecord {
  return {
    id: 1,
    status: "active",
    fincode_subscription_id: "sub_mock_1",
    fincode_plan_id: "plan_mock_basic",
    plan_name: "ベーシック",
    plan_amount: 500,
    plan_interval: "month",
    cancelled_at: null,
    current_period_end: null,
    cancel_at_period_end: false,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides
  };
}

export function buildPlan(overrides: Partial<Plan> = {}): Plan {
  return {
    fincode_plan_id: "plan_mock_basic",
    name: "ベーシック",
    amount: 500,
    currency: "JPY",
    interval: "month",
    ...overrides
  };
}

export function buildCard(overrides: Partial<Card> = {}): Card {
  return {
    id: 77,
    brand: "VISA",
    last4: "4242",
    exp_month: 12,
    exp_year: 2030,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides
  };
}

export function buildHistoryItem(overrides: Partial<HistoryItem> = {}): HistoryItem {
  return {
    id: 1,
    status: "succeeded",
    amount: 980,
    fincode_payment_id: "pay_1",
    charged_at: "2026-02-01T00:00:00Z",
    ...overrides
  };
}

export function buildHistoryPage(
  items: HistoryItem[] = [],
  overrides: Partial<Omit<PaginatedBillingHistory, "data">> = {}
): PaginatedBillingHistory {
  return {
    data: items,
    page: 1,
    per_page: 10,
    total: items.length,
    ...overrides
  };
}
