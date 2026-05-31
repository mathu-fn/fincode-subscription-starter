import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { LoadingButton } from "../components/LoadingButton";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../lib/apiClient";
import { authFormClass, authLinkClass } from "../lib/styles";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="mx-auto grid max-w-md gap-6">
      <h1 className="text-3xl font-bold text-sky-950">ログイン</h1>
      <ErrorBanner error={error} />
      <form onSubmit={onSubmit} className={authFormClass}>
        <FormField
          label="メールアドレス"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
        <FormField
          label="パスワード"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
        <LoadingButton type="submit" isLoading={submitting} loadingLabel="ログイン中...">
          ログイン
        </LoadingButton>
      </form>
      <p className="text-sm text-slate-600">
        アカウントをお持ちでない方は{" "}
        <Link to="/register" className={authLinkClass}>
          こちら
        </Link>{" "}
        から登録できます。
      </p>
    </section>
  );
}
