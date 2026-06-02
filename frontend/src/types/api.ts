export type Subscription = {
  id: number;
  status: string;
  fincode_subscription_id: string | null;
  fincode_plan_id: string;
  plan_name: string;
  plan_amount: number;
  plan_interval: string;
  cancelled_at: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string;
} | null;

export type Plan = {
  fincode_plan_id: string;
  name: string;
  amount: number;
  currency: string;
  interval: string;
};

export type Card = {
  id: number;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  created_at: string;
};

export type HistoryItem = {
  id: number;
  status: string;
  amount: number;
  fincode_payment_id: string | null;
  charged_at: string;
};

export type PaginatedBillingHistory = {
  data: HistoryItem[];
  page: number;
  per_page: number;
  total: number;
};
