import { useEffect, useId, useRef } from "react";
import type { ReactNode } from "react";

import { mutedTextClass, secondaryBtn } from "../lib/styles";
import type { ButtonVariant } from "../types/ui";

import { LoadingButton } from "./LoadingButton";

type ConfirmDialogProps = {
  open: boolean;
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  loadingLabel?: string;
  variant?: Extract<ButtonVariant, "primary" | "danger">;
  isConfirming?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "実行",
  cancelLabel = "キャンセル",
  loadingLabel = "処理中...",
  variant = "danger",
  isConfirming = false,
  onConfirm,
  onCancel
}: ConfirmDialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isConfirming) {
        e.preventDefault();
        onCancel();
      }
    };
    document.addEventListener("keydown", onKey);
    cancelRef.current?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, isConfirming, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !isConfirming) onCancel();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        className="w-full max-w-md border border-line bg-white p-6"
      >
        <h2 id={titleId} className="font-dot text-xl tracking-tight text-black">
          {title}
        </h2>
        {description && (
          <div id={descriptionId} className={`mt-3 ${mutedTextClass}`}>
            {description}
          </div>
        )}
        <div className="mt-6 flex flex-wrap justify-end gap-3">
          <button
            type="button"
            ref={cancelRef}
            onClick={onCancel}
            disabled={isConfirming}
            className={`${secondaryBtn} disabled:cursor-not-allowed disabled:opacity-60`}
          >
            {cancelLabel}
          </button>
          <LoadingButton
            type="button"
            variant={variant}
            isLoading={isConfirming}
            loadingLabel={loadingLabel}
            onClick={onConfirm}
          >
            {confirmLabel}
          </LoadingButton>
        </div>
      </div>
    </div>
  );
}
