import type { ButtonHTMLAttributes, ReactNode } from "react";

import type { ButtonVariant } from "../types/ui";

type LoadingButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  isLoading?: boolean;
  loadingLabel?: ReactNode;
  variant?: ButtonVariant;
};

const baseClass =
  "inline-flex min-h-11 items-center justify-center gap-2 border px-5 py-2.5 text-sm font-semibold transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "border-sky-600 bg-sky-500 text-white hover:bg-sky-600 focus:ring-sky-500 focus:ring-offset-white",
  danger:
    "border-red-700 bg-red-600 text-white hover:bg-red-700 focus:ring-red-600 focus:ring-offset-white",
  ghost:
    "border-transparent bg-transparent px-0 py-0 text-sky-700 hover:text-sky-900 focus:ring-sky-500 focus:ring-offset-white"
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
        <span
          aria-hidden="true"
          className="h-4 w-4 animate-spin border-2 border-current border-t-transparent"
        />
      )}
      <span>{isLoading ? loadingLabel ?? children : children}</span>
    </button>
  );
}
