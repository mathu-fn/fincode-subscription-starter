// 契約 / 決済ステータスを日本語ラベル + 色付きバッジで表示する。
// バックエンドが返す生の status 文字列（active / cancelled / unpaid / succeeded /
// failed、および fincode が送ってくる任意の文字列）をそのまま受け取り、表示だけを
// 変換する。制御フロー（sub.status === "active" などの比較）はこのコンポーネントの
// 外側で生の文字列のまま行う。

type StatusStyle = {
  label: string;
  className: string;
};

// 既知のステータスの表示マップ。未知の値はフォールバック（生の文字列 + グレー）で出す。
const STATUS_STYLES: Record<string, StatusStyle> = {
  active: { label: "契約中", className: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  cancelled: { label: "解約済み", className: "border-slate-200 bg-slate-100 text-slate-600" },
  unpaid: { label: "未払い", className: "border-amber-200 bg-amber-50 text-amber-700" },
  succeeded: { label: "成功", className: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  failed: { label: "失敗", className: "border-red-200 bg-red-50 text-red-700" }
};

const FALLBACK_CLASS = "border-slate-200 bg-slate-100 text-slate-600";
const BASE_CLASS = "inline-flex items-center gap-1.5 border px-2.5 py-0.5 text-xs font-semibold";

type StatusBadgeProps = {
  status: string;
  className?: string;
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const style = STATUS_STYLES[status];
  // 未知のステータスでも値を落とさず、生の文字列をそのまま見せる。
  const label = style?.label ?? status;
  const colorClass = style?.className ?? FALLBACK_CLASS;
  return (
    <span className={`${BASE_CLASS} ${colorClass}${className ? ` ${className}` : ""}`}>{label}</span>
  );
}
