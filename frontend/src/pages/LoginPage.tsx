import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingButton } from "../components/LoadingButton";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../lib/apiClient";

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
      <form onSubmit={onSubmit} className="grid gap-4 border border-sky-200 bg-white p-6 shadow-sm shadow-sky-100">
        <label className="grid gap-1.5 text-sm font-semibold text-slate-700">
          <span>メールアドレス</span>
          <input
            className="min-h-11 border border-sky-200 bg-white px-3 py-2 text-base font-normal text-slate-900 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-200"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </label>
        <label className="grid gap-1.5 text-sm font-semibold text-slate-700">
          <span>パスワード</span>
          <input
            className="min-h-11 border border-sky-200 bg-white px-3 py-2 text-base font-normal text-slate-900 outline-none transition focus:border-sky-500 focus:ring-2 focus:ring-sky-200"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        <LoadingButton type="submit" isLoading={submitting} loadingLabel="ログイン中...">
          ログイン
        </LoadingButton>
      </form>
      <p className="text-sm text-slate-600">
        アカウントをお持ちでない方は{" "}
        <Link to="/register" className="font-semibold text-sky-700 hover:text-sky-900">
          こちら
        </Link>{" "}
        から登録できます。
      </p>
    </section>
  );
}
