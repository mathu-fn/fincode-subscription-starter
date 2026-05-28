import { Link } from "react-router-dom";

const GITHUB_URL = "https://github.com/ltac0203-pixel/fincode-subscription-starter";

const badgeClass =
  "inline-flex items-center gap-1.5 border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700";
const primaryBtn =
  "inline-flex min-h-11 items-center justify-center border border-sky-600 bg-sky-500 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2";
const secondaryBtn =
  "inline-flex min-h-11 items-center justify-center border border-sky-600 bg-white px-6 py-3 text-sm font-semibold text-sky-700 transition-colors hover:bg-sky-50 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2";
const sectionTitle = "text-2xl font-bold text-sky-950 sm:text-3xl";
const cardClass = "border border-sky-200 bg-white p-6 shadow-sm shadow-sky-100";
const codeChip = "bg-sky-50 px-1.5 py-0.5 font-mono text-[0.85em] text-sky-800";

const features: Array<{ title: string; description: string }> = [
  {
    title: "ユーザー登録 / JWT 認証",
    description:
      "pwdlib (argon2) によるパスワードハッシュと JWT Bearer。/api/register と /api/login を最小構成で提供します。"
  },
  {
    title: "カードトークン化",
    description:
      "fincode.js の UI コンポーネントを React に組み込み、PAN / CVC をバックエンドに送らずトークンのみを REST に渡します。"
  },
  {
    title: "プラン表示と契約登録",
    description:
      "fincode から契約可能なプラン一覧を取得し、契約時には plan_snapshot を JSONB で永続化して履歴の意味を保ちます。"
  },
  {
    title: "解約フロー",
    description:
      "fincode に即時解約要求 → ローカル status を cancelled に更新。期間末までのアクセス可否は業務側で判断します。"
  },
  {
    title: "Webhook 受信と冪等性",
    description:
      "Fincode-Signature の HMAC-SHA256 検証 + webhook_events_seen と subscription_results upsert の二段冪等で再送に強い。"
  },
  {
    title: "決済履歴 / ページング",
    description:
      "subscription_results に 1 課金 1 行で書き込まれた決済結果を、フロントからページング付きで参照できます。"
  },
  {
    title: "監査ログ",
    description:
      "成功した業務操作は audit_logs に before / after JSONB で記録、失敗は構造化ログにのみ残し PII 漏洩を避けます。"
  },
  {
    title: "カード soft delete",
    description:
      "fincode_cards.deleted_at で論理削除。過去契約と監査ログの説明可能性を維持し、誤削除からの復旧余地を残します。"
  },
  {
    title: "OpenAPI 仕様",
    description:
      "公開 API は docs/api/openapi.yml に定義し、Redocly で lint 通過済み。クライアント自動生成にもそのまま使えます。"
  }
];

const stack: Array<[string, string]> = [
  ["フロントエンド", "React + Vite + TypeScript + Tailwind"],
  ["バックエンド", "FastAPI + Python 3.11+ (uv)"],
  ["データベース", "PostgreSQL 16+"],
  ["ORM / マイグレーション", "SQLAlchemy 2.x async + Alembic"],
  ["認証", "JWT Bearer + pwdlib (argon2)"],
  ["決済", "fincode 定期課金"],
  ["テスト", "pytest + testcontainers + Vitest"]
];

const quickstartSteps: Array<{ title: string; command: string }> = [
  {
    title: "1. PostgreSQL を起動",
    command: "docker compose up -d postgres"
  },
  {
    title: "2. バックエンド (FastAPI)",
    command: "cd backend\nuv sync\nuv run alembic upgrade head\nuv run uvicorn app.main:app --reload"
  },
  {
    title: "3. フロントエンド (Vite)",
    command: "cd frontend\nnpm install\nnpm run dev"
  }
];

export function LandingPage() {
  return (
    <div className="mx-auto grid max-w-6xl gap-16 pb-12">
      <section className="grid gap-6 pt-4 sm:pt-8">
        <div className="flex flex-wrap items-center gap-2">
          <span className={badgeClass}>OSS リファレンス実装</span>
          <span className={badgeClass}>Apache 2.0</span>
          <span className={badgeClass}>fincode 定期課金</span>
          <span className={badgeClass}>React + FastAPI</span>
        </div>
        <h1 className="text-4xl font-bold leading-tight text-sky-950 sm:text-5xl">
          fincode の定期課金を、
          <br className="hidden sm:block" />
          <span className="text-sky-600">プロダクション水準で</span>取り込む。
        </h1>
        <p className="max-w-3xl text-base text-slate-700 sm:text-lg">
          React + FastAPI で fincode の定期課金を実装する OSS リファレンスです。カードのトークン化、サブスクリプション登録・解約、Webhook の冪等処理、監査ログまで、そのまま自社サービスに取り込める形で提供します。
        </p>
        <div className="flex flex-wrap gap-3">
          <Link to="/register" className={primaryBtn}>
            デモを試す（新規登録）
          </Link>
          <Link to="/login" className={secondaryBtn}>
            ログイン
          </Link>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={secondaryBtn}
          >
            GitHub で見る →
          </a>
        </div>
        <p className="text-xs text-slate-500">
          テスト用 fincode キー（<code className={codeChip}>m_test_*</code> / <code className={codeChip}>p_test_*</code>）と <code className={codeChip}>https://api.test.fincode.jp</code> の組み合わせで、すぐ動かせます。
        </p>
      </section>

      <section className="grid gap-6">
        <h2 className={sectionTitle}>なぜこのリファレンス実装か</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <article className={cardClass}>
            <h3 className="text-lg font-bold text-sky-950">PAN / CVC はサーバーに来ない</h3>
            <p className="mt-3 text-sm leading-relaxed text-slate-600">
              ブラウザ上の fincode.js でトークン化し、REST にはカードトークンのみ送信。バックエンドはカード番号や CVC を一度も保持しません。PCI DSS の影響範囲を最小化する設計です。
            </p>
          </article>
          <article className={cardClass}>
            <h3 className="text-lg font-bold text-sky-950">本番想定の堅牢な実装</h3>
            <p className="mt-3 text-sm leading-relaxed text-slate-600">
              fincode 書き込みの Idempotency-Key 再利用、5xx / タイムアウト時のリトライ、Circuit Breaker、partial unique index による「1 ユーザー 1 アクティブ契約」の DB 保証など、エッジケースに最初から備えています。
            </p>
          </article>
          <article className={cardClass}>
            <h3 className="text-lg font-bold text-sky-950">自社サービスに移植しやすい</h3>
            <p className="mt-3 text-sm leading-relaxed text-slate-600">
              fincode 直接呼び出しは <code className={codeChip}>app/services/fincode/</code> に閉じ込め、Manager 層と REST 層の責務が厳格に分かれています。ドメインロジックの切り出しが容易な構成です。
            </p>
          </article>
        </div>
      </section>

      <section className="grid gap-6">
        <h2 className={sectionTitle}>含まれている機能</h2>
        <ul className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => (
            <li key={feature.title} className={cardClass}>
              <h3 className="font-bold text-sky-950">{feature.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-600">{feature.description}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-6">
        <h2 className={sectionTitle}>アーキテクチャ</h2>
        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <article className={cardClass}>
            <h3 className="text-lg font-bold text-sky-950">レイヤと責務</h3>
            <pre className="mt-4 overflow-x-auto bg-sky-50 p-4 text-xs leading-relaxed text-slate-800">
{`React UI (frontend/src/)
   ↓ REST + JWT Bearer
FastAPI Router (app/api/routes/)
   ↓ Depends(...)
Dependencies (deps / security)
   ↓
Domain Managers (app/services/)
   ↓                       ↓
Fincode Services           PostgreSQL
(app/services/fincode/)
   ↓
FincodeHttpClient → fincode API`}
            </pre>
            <p className="mt-3 text-sm leading-relaxed text-slate-600">
              逆方向の参照は禁止。fincode への HTTP 呼び出しは fincode サービス層に集中し、API ルートや Manager 層から直接 httpx を叩くことはありません。
            </p>
          </article>
          <article className={cardClass}>
            <h3 className="text-lg font-bold text-sky-950">技術スタック</h3>
            <dl className="mt-4 grid gap-2 text-sm">
              {stack.map(([k, v]) => (
                <div key={k} className="grid gap-1 bg-sky-50 px-3 py-2 sm:grid-cols-[10rem_1fr] sm:items-center sm:gap-3">
                  <dt className="text-slate-500">{k}</dt>
                  <dd className="font-semibold text-slate-900">{v}</dd>
                </div>
              ))}
            </dl>
          </article>
        </div>
      </section>

      <section className="grid gap-6">
        <h2 className={sectionTitle}>クイックスタート</h2>
        <p className="text-slate-700">
          Docker で PostgreSQL を起動し、バックエンドとフロントエンドをローカルで立てる 3 プロセス構成が標準です。
        </p>
        <div className="grid gap-4 md:grid-cols-3">
          {quickstartSteps.map((step) => (
            <article key={step.title} className={cardClass}>
              <h3 className="font-bold text-sky-950">{step.title}</h3>
              <pre className="mt-3 overflow-x-auto bg-slate-950 p-3 text-xs leading-relaxed text-sky-100">
{step.command}
              </pre>
            </article>
          ))}
        </div>
        <p className="text-sm leading-relaxed text-slate-600">
          初回は <code className={codeChip}>.env.example</code> を <code className={codeChip}>.env</code> へコピーし、fincode 管理画面で発行したテスト環境キーを設定してください。詳しい手順は README と <code className={codeChip}>docs/getting-started/</code> を参照。
        </p>
      </section>

      <section className="border border-sky-200 bg-white p-8 shadow-sm shadow-sky-100">
        <div className="flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-2xl">
            <h2 className="text-2xl font-bold text-sky-950">まずはローカルで触ってみる。</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              新規登録するとデモのダッシュボードに入り、カード追加 → プラン契約 → 履歴確認まで一通り試せます。fincode のテストカード番号で動作確認できます。
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/register" className={primaryBtn}>
              新規登録
            </Link>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className={secondaryBtn}
            >
              GitHub
            </a>
          </div>
        </div>
      </section>

      <footer className="border-t border-sky-200 pt-6 text-xs leading-relaxed text-slate-500">
        <p>
          Apache License 2.0 / コントリビュートは同ライセンス下で配布されることに同意したものとみなされます。fincode は GMO Payment Gateway 株式会社の決済サービスです。
        </p>
      </footer>
    </div>
  );
}
