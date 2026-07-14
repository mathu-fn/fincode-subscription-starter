// 契約 / 決済ステータスを日本語ラベルで表示する。
// バックエンドが返す生の status 文字列（active / cancelled / unpaid / succeeded /
// failed、および fincode が送ってくる任意の文字列）をそのまま受け取り、表示だけを
// 変換する。制御フロー（sub.status === "active" などの比較）はこのコンポーネントの
// 外側で生の文字列のまま行う。
//
// DESIGN 準拠: 色で塗り分けない（赤は「点」であり 1 画面 1〜2 箇所まで）。バッジは
// 一律モノクロ（等幅大文字 + 1px 薄枠 + グレーの小ドット）で、区別は文言で行う。
// アクティブ契約の「ライブ」を示す赤ドットは HomePage 側の 1 点だけに限定する。

// 既知のステータスの日本語ラベル。未知の値はフォールバック（生の文字列）で出す。
const STATUS_LABELS: Record<string, string> = {
  active: "契約中",
  cancelled: "解約済み",
  unpaid: "未払い",
  succeeded: "成功",
  failed: "失敗"
};

const BASE_CLASS =
  "inline-flex items-center gap-1.5 border border-line bg-white px-2.5 py-0.5 font-mono text-xs uppercase tracking-[0.08em] text-black";

type StatusBadgeProps = {
  status: string;
  className?: string;
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  // 未知のステータスでも値を落とさず、生の文字列をそのまま見せる。
  const label = STATUS_LABELS[status] ?? status;
  return (
    <span className={`${BASE_CLASS}${className ? ` ${className}` : ""}`}>
      <span aria-hidden className="inline-block h-1.5 w-1.5 bg-neutral-400" />
      {label}
    </span>
  );
}
