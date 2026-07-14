// Nothing の看板記号: 8px の小さな四角ドット + 等幅ラベル。
// 赤（variant="live"）はアクティブ/ライブ状態の 1 点だけに使う——赤は「点」であり、
// 1 画面 1〜2 箇所まで。それ以外はモノクロのグレードット（variant="muted"）。
// 常時アニメーションは付けない（DESIGN 準拠、静的）。
type StatusDotVariant = "live" | "muted";

type StatusDotProps = {
  variant?: StatusDotVariant;
  label?: string;
  className?: string;
};

export function StatusDot({ variant = "muted", label, className }: StatusDotProps) {
  const dotColor = variant === "live" ? "bg-accent" : "bg-neutral-400";
  return (
    <span className={`inline-flex items-center gap-2${className ? ` ${className}` : ""}`}>
      <span aria-hidden className={`inline-block h-2 w-2 ${dotColor}`} />
      {label ? (
        <span className="font-mono text-xs uppercase tracking-[0.1em] text-black">{label}</span>
      ) : null}
    </span>
  );
}
