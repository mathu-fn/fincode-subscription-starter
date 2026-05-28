import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ConfirmDialog } from "../components/ConfirmDialog";
import { LoadingButton } from "../components/LoadingButton";
import { useAuth } from "../hooks/useAuth";

export function AccountPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  async function handleLogout() {
    setIsSubmitting(true);
    try {
      await logout();
      navigate("/login", { replace: true });
    } finally {
      setIsSubmitting(false);
      setConfirmOpen(false);
    }
  }

  return (
    <section className="mx-auto grid max-w-5xl gap-6">
      <header>
        <h1 className="text-3xl font-bold text-sky-950">アカウント</h1>
        <p className="mt-2 text-sm text-slate-600">ログイン情報の確認とログアウトができます。</p>
      </header>

      <article className="border border-sky-200 bg-white p-6 shadow-sm shadow-sky-100">
        <dl className="grid gap-4 sm:grid-cols-2">
          <div className="bg-sky-50 p-4">
            <dt className="text-sm text-slate-500">名前</dt>
            <dd className="mt-1 font-semibold text-slate-900">{user?.name ?? "-"}</dd>
          </div>
          <div className="bg-sky-50 p-4">
            <dt className="text-sm text-slate-500">メールアドレス</dt>
            <dd className="mt-1 font-semibold text-slate-900">{user?.email ?? "-"}</dd>
          </div>
        </dl>
        <div className="mt-6">
          <LoadingButton
            type="button"
            variant="danger"
            isLoading={isSubmitting}
            loadingLabel="ログアウト中..."
            onClick={() => setConfirmOpen(true)}
          >
            ログアウト
          </LoadingButton>
        </div>
      </article>

      <ConfirmDialog
        open={confirmOpen}
        title="ログアウトしますか？"
        description="現在のセッションを終了します。再度ご利用にはログインが必要です。"
        confirmLabel="ログアウト"
        loadingLabel="ログアウト中..."
        variant="danger"
        isConfirming={isSubmitting}
        onConfirm={handleLogout}
        onCancel={() => setConfirmOpen(false)}
      />
    </section>
  );
}
