import { Card } from "../../components/Card";
import { LoadingButton } from "../../components/LoadingButton";
import { SpecRow, SpecTable } from "../../components/SpecTable";
import { StatusBadge } from "../../components/StatusBadge";
import { StatusDot } from "../../components/StatusDot";
import { primaryLinkClass, sectionClass, sectionTitle } from "../../lib/styles";
import type { Subscription } from "../../types/api";

import { formatDateTime, formatPlanPrice } from "./utils";

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
        <h2 className={sectionTitle}>契約</h2>
        {/* この画面で唯一の赤い「点」。アクティブ契約のライブ状態だけを示す。 */}
        {sub?.status === "active" && <StatusDot variant="live" label="契約中" />}
      </div>
      {!subscriptionLoaded ? (
        <p className="text-sm text-muted">読み込み中...</p>
      ) : !sub ? (
        <Card className="p-4">
          <p className="text-muted">アクティブな契約はありません。</p>
          <p className="mt-4">
            <a href="#plans" className={primaryLinkClass}>
              プランを選ぶ
            </a>
          </p>
        </Card>
      ) : (
        <Card className="p-4">
          <SpecTable>
            <SpecRow label="プラン">{sub.plan_name}</SpecRow>
            <SpecRow label="金額">
              <span className="font-mono">{formatPlanPrice(sub.plan_amount, sub.plan_interval)}</span>
            </SpecRow>
            <SpecRow label="状態">
              <span className="inline-flex items-center gap-2">
                <StatusBadge status={sub.status} />
                {sub.cancel_at_period_end && (
                  <span className="font-mono text-xs uppercase tracking-[0.08em] text-muted">
                    解約予約中
                  </span>
                )}
              </span>
            </SpecRow>
            <SpecRow label="契約日">{formatDateTime(sub.created_at)}</SpecRow>
            {sub.cancelled_at && (
              <SpecRow label={sub.cancel_at_period_end ? "解約申込日" : "解約日"}>
                {formatDateTime(sub.cancelled_at)}
              </SpecRow>
            )}
            {sub.current_period_end && (
              <SpecRow label={sub.cancel_at_period_end ? "利用可能期限" : "現在の請求期間終了"}>
                {formatDateTime(sub.current_period_end)}
              </SpecRow>
            )}
          </SpecTable>
          {sub.cancel_at_period_end && sub.current_period_end && (
            <p className="mt-6 text-sm text-muted">
              この契約は {formatDateTime(sub.current_period_end)} まで利用できます。
            </p>
          )}
          {sub.status === "unpaid" && (
            <p className="mt-6 text-sm font-medium text-black">
              お支払いが確認できませんでした。カードをご確認のうえ変更いただくか、プランを変更してください。
            </p>
          )}
          {(sub.status === "active" || sub.status === "unpaid") && !sub.cancel_at_period_end && (
            <p className="mt-6">
              <LoadingButton
                type="button"
                variant="danger"
                isLoading={cancelling}
                loadingLabel="解約中..."
                onClick={onRequestCancel}
              >
                解約する
              </LoadingButton>
            </p>
          )}
        </Card>
      )}
    </section>
  );
}
