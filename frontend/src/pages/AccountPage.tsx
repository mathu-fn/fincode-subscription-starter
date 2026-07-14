import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Card } from "../components/Card";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { LoadingButton } from "../components/LoadingButton";
import { SpecRow, SpecTable } from "../components/SpecTable";
import { useAuth } from "../hooks/useAuth";
import { mutedTextClass, sectionTitle } from "../lib/styles";

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
        <h1 className={sectionTitle}>アカウント</h1>
        <p className={`mt-2 ${mutedTextClass}`}>ログイン情報の確認とログアウトができます。</p>
      </header>

      <Card className="p-6">
        <SpecTable>
          <SpecRow label="名前">{user?.name ?? "-"}</SpecRow>
          <SpecRow label="メールアドレス">{user?.email ?? "-"}</SpecRow>
        </SpecTable>
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
      </Card>

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
