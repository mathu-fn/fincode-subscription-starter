import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../lib/apiClient";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError(new Error("お名前を入力してください。"));
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await register(trimmedName, email.trim(), password);
      navigate("/", { replace: true });
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page page-narrow">
      <h1>新規登録</h1>
      <ErrorBanner error={error} />
      <form onSubmit={onSubmit} className="form">
        <label className="field">
          <span>お名前</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={100}
          />
        </label>
        <label className="field">
          <span>メールアドレス</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            maxLength={255}
            autoComplete="email"
          />
        </label>
        <label className="field">
          <span>パスワード（8文字以上）</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>
        <button type="submit" className="primary" disabled={submitting}>
          {submitting ? "登録中..." : "登録"}
        </button>
      </form>
      <p className="hint">
        既にアカウントをお持ちの方は <Link to="/login">こちら</Link> からログイン。
      </p>
    </section>
  );
}
