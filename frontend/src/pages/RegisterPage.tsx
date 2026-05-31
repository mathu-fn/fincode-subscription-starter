import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { LoadingButton } from "../components/LoadingButton";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../lib/apiClient";
import { authFormClass, authLinkClass } from "../lib/styles";

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
    <section className="mx-auto grid max-w-md gap-6">
      <h1 className="text-3xl font-bold text-sky-950">新規登録</h1>
      <ErrorBanner error={error} />
      <form onSubmit={onSubmit} className={authFormClass}>
        <FormField
          label="お名前"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={100}
        />
        <FormField
          label="メールアドレス"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          maxLength={255}
          autoComplete="email"
        />
        <FormField
          label="パスワード（8文字以上）"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          autoComplete="new-password"
        />
        <LoadingButton type="submit" isLoading={submitting} loadingLabel="登録中...">
          登録
        </LoadingButton>
      </form>
      <p className="text-sm text-slate-600">
        既にアカウントをお持ちの方は{" "}
        <Link to="/login" className={authLinkClass}>
          こちら
        </Link>{" "}
        からログイン。
      </p>
    </section>
  );
}
