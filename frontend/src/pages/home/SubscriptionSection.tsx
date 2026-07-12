import { LoadingButton } from "../../components/LoadingButton";
import { StatusBadge } from "../../components/StatusBadge";
import { formatDateTime, formatPlanPrice } from "../../lib/format";
import { primaryLinkClass, sectionClass } from "../../lib/styles";
import type { Subscription } from "../../types/api";
import { cardClass } from "./styles";

type SubscriptionSectionProps = {
  subscriptionLoaded: boolean;
  sub: Subscription;
  cancelling: boolean;
  onRequestCancel: () => void;
};

export function SubscriptionSection({
  subscriptionLoaded,
  sub,
  cancelling,
  onRequestCancel
}: SubscriptionSectionProps) {
  return (
    <section id="subscription" className={sectionClass}>
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-xl font-bold text-sky-950">契約</h2>
      </div>
      {!subscriptionLoaded ? (
        <p className="text-slate-600">読み込み中...</p>
      ) : !sub ? (
        <article className={cardClass}>
          <p className="text-slate-700">アクティブな契約はありません。</p>
          <p className="mt-4">
            <a href="#plans" className={primaryLinkClass}>
              プランを選ぶ
            </a>
          </p>
        </article>
      ) : (
        <article className={cardClass}>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="bg-sky-50 p-4">
              <dt className="text-sm text-slate-500">プラン</dt>
              <dd className="mt-1 font-semibold text-slate-900">{sub.plan_name}</dd>
            </div>
            <div className="bg-sky-50 p-4">
              <dt className="text-sm text-slate-500">金額</dt>
              <dd className="mt-1 font-semibold text-slate-900">{formatPlanPrice(sub.plan_amount, sub.plan_interval)}</dd>
            </div>
            <div className="bg-sky-50 p-4">
              <dt className="text-sm text-slate-500">状態</dt>
              <dd className="mt-1">
                <StatusBadge status={sub.status} />
                {sub.cancel_at_period_end && (
                  <span className="ml-2 text-sm font-semibold text-amber-700">解約予約中</span>
                )}
              </dd>
            </div>
            <div className="bg-sky-50 p-4">
              <dt className="text-sm text-slate-500">契約日</dt>
              <dd className="mt-1 font-semibold text-slate-900">{formatDateTime(sub.created_at)}</dd>
            </div>
            {sub.cancelled_at && (
              <div className="bg-sky-50 p-4">
                <dt className="text-sm text-slate-500">{sub.cancel_at_period_end ? "解約申込日" : "解約日"}</dt>
                <dd className="mt-1 font-semibold text-slate-900">{formatDateTime(sub.cancelled_at)}</dd>
              </div>
            )}
            {sub.current_period_end && (
              <div className="bg-sky-50 p-4">
                <dt className="text-sm text-slate-500">
                  {sub.cancel_at_period_end ? "利用可能期限" : "現在の請求期間終了"}
                </dt>
                <dd className="mt-1 font-semibold text-slate-900">{formatDateTime(sub.current_period_end)}</dd>
              </div>
            )}
          </dl>
          {sub.cancel_at_period_end && sub.current_period_end && (
            <p className="mt-6 text-sm font-semibold text-amber-700">
              この契約は {formatDateTime(sub.current_period_end)} まで利用できます。
            </p>
          )}
          {sub.status === "unpaid" && (
            <p className="mt-6 text-sm font-semibold text-rose-700">
              お支払いが確認できませんでした。カードをご確認のうえ変更いただくか、プランを変更してください。
            </p>
          )}
          {(sub.status === "active" || sub.status === "unpaid") && !sub.cancel_at_period_end && (
            <p className="mt-6">
              <LoadingButton type="button" variant="danger" isLoading={cancelling} loadingLabel="解約中..." onClick={onRequestCancel}>
                解約する
              </LoadingButton>
            </p>
          )}
        </article>
      )}
    </section>
  );
}
