import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function AccountPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);

  return (
    <section className="page">
      <header>
        <h1>アカウント</h1>
        <p className="hint">ログイン情報の確認とログアウトができます。</p>
      </header>

      <article className="card">
        <dl className="meta">
          <div>
            <dt>名前</dt>
            <dd>{user?.name ?? "-"}</dd>
          </div>
          <div>
            <dt>メールアドレス</dt>
            <dd>{user?.email ?? "-"}</dd>
          </div>
        </dl>
        <div className="actions">
          <button
            type="button"
            className="danger"
            disabled={isSubmitting}
            onClick={async () => {
              setIsSubmitting(true);
              try {
                await logout();
                navigate("/login", { replace: true });
              } finally {
                setIsSubmitting(false);
              }
            }}
          >
            {isSubmitting ? "ログアウト中..." : "ログアウト"}
          </button>
        </div>
      </article>
    </section>
  );
}
