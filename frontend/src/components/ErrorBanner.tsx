import type { ApiError } from "../lib/apiClient";

const codeLabels: Record<string, string> = {
  invalid_credentials: "認証情報が正しくありません。もう一度ログインしてください。",
  invalid_google_token: "Google ログインに失敗しました。もう一度お試しください。",
  google_email_not_verified: "Google アカウントのメールアドレスが未確認のためログインできません。",
  email_already_registered: "このメールアドレスは既存のアカウントで使用されています。",
  active_subscription_exists: "すでに有効なサブスクリプションがあります。",
  card_in_use: "アクティブな契約で利用中のカードは削除できません。",
  card_not_found: "対象のカードが見つかりません。",
  expired_card: "カードの有効期限が切れています。",
  plan_unavailable: "選択したプランは現在利用できません。",
  subscription_not_found: "アクティブなサブスクリプションがありません。",
  forbidden: "この操作は許可されていません。",
  unauthenticated: "ログインが必要です。",
  validation_error: "入力内容を確認してください。",
  rate_limited: "リクエストが多すぎます。少し時間をおいて再度お試しください。",
  fincode_api_error: "決済サービスとの通信に失敗しました。",
  fincode_rate_limited: "決済サービスへのリクエストが集中しています。少し時間をおいて再度お試しください。",
  fincode_server_error: "決済サービスでエラーが発生しました。少し時間をおいて再度お試しください。",
  fincode_timeout: "決済サービスとの通信がタイムアウトしました。少し時間をおいて再度お試しください。",
  fincode_unavailable: "決済サービスが一時的に利用できません。"
};

export function ErrorBanner({ error }: { error: ApiError | Error | null }) {
  if (!error) return null;
  const code = "code" in error ? (error as ApiError).code : "error";
  const label = codeLabels[code] ?? error.message;
  // 赤は面で塗らず、細い左罫線の 1 点だけに使う。本文は黒、キャプションは等幅。
  return (
    <div
      className="flex gap-2 border-l-2 border-accent bg-white px-4 py-3 text-sm text-black"
      role="alert"
    >
      <strong className="font-mono text-xs uppercase tracking-[0.1em] text-accent">エラー：</strong>
      <span>{label}</span>
    </div>
  );
}
