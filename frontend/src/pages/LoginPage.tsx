import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { ErrorBanner } from "../components/ErrorBanner";
import { useAuth } from "../hooks/useAuth";
import { ApiError } from "../lib/apiClient";
import { initGoogleIdentity, renderGoogleButton } from "../lib/googleIdentity";
import { authFormClass } from "../lib/styles";
import type { AppError } from "../types/ui";

export function LoginPage() {
  const { loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";

  const buttonRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<AppError>(null);
  const [submitting, setSubmitting] = useState(false);

  const onCredential = useCallback(
    async (credential: string) => {
      setError(null);
      setSubmitting(true);
      try {
        await loginWithGoogle(credential);
        navigate(from, { replace: true });
      } catch (e) {
        setError(e as ApiError);
      } finally {
        setSubmitting(false);
      }
    },
    [from, loginWithGoogle, navigate]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await initGoogleIdentity((credential) => {
          void onCredential(credential);
        });
        if (!cancelled && buttonRef.current) {
          await renderGoogleButton(buttonRef.current);
        }
      } catch (e) {
        // スクリプトのロード失敗（オフライン・CSP ブロック等）も無言にしない。
        if (!cancelled) setError(e as Error);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [onCredential]);

  return (
    <section className="mx-auto grid max-w-md gap-6">
      <h1 className="text-3xl font-bold text-sky-950">ログイン</h1>
      <ErrorBanner error={error} />
      <div className={authFormClass}>
        <p className="text-sm text-slate-600">
          Google アカウントでログインします。初めての方もそのままアカウントが作成されます。
        </p>
        <div ref={buttonRef} aria-label="Google でログイン" />
        {submitting ? <p className="text-sm text-slate-600">ログイン中...</p> : null}
      </div>
    </section>
  );
}
