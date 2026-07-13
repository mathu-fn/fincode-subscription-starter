import type { ButtonHTMLAttributes, ReactNode } from "react";

import type { ButtonVariant } from "../types/ui";

type LoadingButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  isLoading?: boolean;
  loadingLabel?: ReactNode;
  variant?: ButtonVariant;
};

// 等幅・大文字・レタースペーシングのモノクロボタン。色は信号としてのみ使う。
const baseClass =
  "inline-flex min-h-11 items-center justify-center gap-2 border px-5 py-2.5 font-mono text-xs uppercase tracking-[0.1em] transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

// primary = 黒塗り・ホバーで白黒反転。danger = 赤の枠/文字（面で塗らず、ホバー時のみ反転）。
// ghost = 文字のみ（インラインのテキストリンク用に padding を持たない）。
const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "border-black bg-black text-white hover:bg-white hover:text-black focus:ring-black focus:ring-offset-white",
  danger:
    "border-accent bg-white text-accent hover:bg-accent hover:text-white focus:ring-accent focus:ring-offset-white",
  ghost:
    "border-transparent bg-transparent px-0 py-0 text-black hover:text-muted focus:ring-black focus:ring-offset-white"
};

function classNames(...classes: Array<string | false | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function LoadingButton({
  children,
  className,
  disabled,
  isLoading = false,
  loadingLabel,
  variant = "primary",
  ...props
}: LoadingButtonProps) {
  return (
    <button
      {...props}
      aria-busy={isLoading || undefined}
      className={classNames(baseClass, variantClasses[variant], className)}
      disabled={disabled || isLoading}
    >
      {isLoading && (
        // グローバルで border-radius:0 のため回転する四角のスピナー（ドット系の意匠に合う）。
        <span
          aria-hidden
          className="inline-block h-3 w-3 animate-spin border border-current border-r-transparent"
        />
      )}
      <span>{isLoading ? loadingLabel ?? children : children}</span>
    </button>
  );
}
