# Repository Guidelines

このリポジトリは **fincode の定期課金（サブスクリプション）** を扱う OSS リファレンス実装です。React (Vite + TypeScript) フロント + FastAPI (Python) バックエンド + PostgreSQL の 3 プロセス構成。本書は OSS 貢献者および AI エージェント（[agents.md](https://agents.md) 規約準拠）向けのガイドです。Claude Code 固有の指示は `CLAUDE.md` を参照。

## プロジェクト構成

```
backend/
  app/
    api/routes/       # FastAPI ルータ (auth, cards, subscriptions, webhooks)
    api/deps.py       # 共通依存性注入 (DB session, fincode client, current_user)
    core/             # 設定, 例外, 例外ハンドラ, セキュリティ (JWT)
    models/           # SQLAlchemy モデル (1 ファイル 1 テーブル)
    services/         # ドメインマネージャ層
      fincode/        # fincode API 呼び出しはここに閉じ込める
  alembic/versions/   # マイグレーション (適用済みは編集禁止)
  tests/              # pytest + testcontainers (PostgreSQL 16)
frontend/
  src/                # React UI, App.tsx / main.tsx, lib/fincodeJs.ts
docs/
  api/openapi.yml     # 公開 API 仕様 (変更は Redocly lint 必須)
  architecture/       # overview / data-model / error-handling / branching / commit-guidelines
```

ローカル生成物 (`backend/.venv/`, `backend/.pytest_cache/`, `frontend/node_modules/`, `frontend/dist/`) は編集禁止。

## 開発コマンド

| 用途 | コマンド (リポジトリルートから) |
| --- | --- |
| PostgreSQL 起動 | `docker compose up -d postgres` |
| Python 依存 | `cd backend && uv sync` |
| マイグレーション適用 | `cd backend && uv run alembic upgrade head` |
| マイグレーション作成 | `cd backend && uv run alembic revision -m "msg"` |
| バックエンド起動 | `cd backend && uv run uvicorn app.main:app --reload` |
| バックエンド全テスト | `cd backend && uv run pytest` |
| 単体テスト指定 | `cd backend && uv run pytest tests/test_subscriptions.py::test_xxx` |
| カバレッジ | `cd backend && uv run pytest --cov=app` |
| フロント依存 | `cd frontend && npm install` |
| フロント起動 | `cd frontend && npm run dev` |
| フロントテスト (vitest) | `cd frontend && npm run test:run` |
| フロントビルド | `cd frontend && npm run build` |
| OpenAPI lint | `npx @redocly/cli lint docs/api/openapi.yml` |

**Backend テストは Docker 必須**: `tests/conftest.py` が `testcontainers-python` で PostgreSQL 16 を起動して Alembic を適用する。JSONB と partial unique index を使うため SQLite では代替不可。

## アーキテクチャの不変条件 (必読)

リクエストフロー — 逆方向参照は禁止:

```
React UI ──REST + JWT──▶ FastAPI router ──Depends──▶ Domain Manager ──▶ Fincode Service ──▶ FincodeHttpClient ──▶ fincode API
                                                          │
                                                          └──▶ SQLAlchemy ──▶ PostgreSQL
```

破ったら PR を通さない原則:

- **PAN / CVC / 生のカード情報はバックエンドに来ない**。ブラウザの `fincode.js` (`frontend/src/lib/fincodeJs.ts`) がトークン化し、API にはカードトークンのみ送る。
- **fincode 直接呼び出しは `app/services/fincode/` だけ**。Manager / ルートから `httpx` を直接叩かない。`get_fincode_client()` 依存性経由で `FincodeHttpClient` を注入する。
- **1 ユーザー = 最大 1 アクティブ契約**。本当の保証は `subscriptions` の partial unique index (`WHERE status='active'`)。Python ガードは UX 用。レースは `IntegrityError` → `ActiveSubscriptionExistsError` に翻訳。
- **fincode 書き込みのリトライは同じ Idempotency-Key を再利用** (`app/services/fincode/idempotency.py`)。
- **fincode 4xx / 429 はリトライしない**。Circuit Breaker (`app/services/fincode/circuit_breaker.py`) も加算しない。5xx / タイムアウトのみ。
- **fincode 生レスポンスをクライアントへ返さない**。`app/core/exceptions.py` の型付き例外に翻訳し、`app/core/exception_handlers.py` が `{detail: {code, message}}` にマップ。新規エラーは両ファイル必ず揃える。
- **契約作成時に fincode プラン情報を `subscriptions.plan_snapshot` (JSONB) にスナップショット**。fincode 側で後から名前 / 金額が変わっても過去契約の意味を保つため。
- **Webhook の冪等性**: `webhook_events_seen.fincode_event_id` UNIQUE + `subscription_results.(fincode_subscription_id, fincode_payment_id)` upsert の二段。署名検証は `Fincode-Signature` と `FINCODE_WEBHOOK_SECRET` の HMAC-SHA256。
- **カードは soft delete** (`fincode_cards.deleted_at`)。過去契約と監査ログの説明可能性を保つ。

ドメインモデル要点は `docs/architecture/data-model.md`、例外マッピング全体は `docs/architecture/error-handling.md` を参照。

## コーディング規約

- **Python**: 型ヒント必須、4 space インデント、FastAPI ルートは小さく保ち実装は services 層へ。テストは `test_*.py` / `test_*` 関数。
- **TypeScript / React**: 関数コンポーネント、コンポーネントは PascalCase、変数は camelCase。環境依存値は `VITE_*` (現状フロント API ホストは `VITE_API_BASE_URL` のみ)。
- 新規 import / 副作用 / 例外型を追加する際は、対応する exception_handler や openapi.yml の更新を同じ PR に含める。

## テストの作法

- `pytest_asyncio` の `asyncio_mode = auto` 設定済み — テスト関数は `async def` で OK。
- `conftest.py` の `app_instance` フィクスチャが各テスト前に **全テーブル TRUNCATE** + slowapi rate limiter リセット。
- 認証付きリクエストは `auth_client` フィクスチャ (`registered_user` が `POST /api/register` を叩く)。
- **テストから fincode 実 API を絶対叩かない**。`app.dependency_overrides[get_fincode_client]` で `FincodeClient` プロトコルを満たす fake に差し替える。低レベルの `FincodeHttpClient` テストは `httpx.MockTransport`。
- レーステストは `asyncio.gather` で複数タスク同時実行し partial unique index の挙動を検証 (`tests/test_subscriptions_race.py` 参照)。

## ブランチ / コミット / PR

- **GitHub Flow**: `main` は常にデプロイ可能、作業は短命なトピックブランチ、Squash merge。詳細は `docs/architecture/branching.md`。
- **コミットプレフィックス**: `feat / fix / docs / test / refactor / chore / security` (`docs/architecture/commit-guidelines.md`)。ブランチ名も同じプレフィックス (例 `feat/subscription-pause`)。
- 次の粒度は **必ず別コミット** に分ける:
  - API 契約変更 (`docs/api/openapi.yml` を含む)
  - React UI 変更
  - SQLAlchemy / Alembic スキーマ変更
  - fincode 連携変更
  - テスト / fixture
- PR は変更内容・検証コマンド・関連 Issue を記載。視覚的変更はスクリーンショット添付。

## セキュリティ / 環境変数

`.env` は `backend/app/core/config.py` の `Settings` で読み込み。重要キー:

- `FINCODE_API_KEY` / `FINCODE_PUBLIC_KEY` / `FINCODE_WEBHOOK_SECRET` / `FINCODE_BASE_URL` — fincode 管理画面のテストキー (`m_test_*` / `p_test_*`) と `https://api.test.fincode.jp` の組み合わせ推奨。
- `DATABASE_URL` = `postgresql+asyncpg://...`。Alembic は内部で `+asyncpg → +psycopg` に置換 (`Settings.sync_database_url`)。
- `JWT_SECRET_KEY` を変えると既存トークンは全部無効化。
- `CORS_ORIGINS` はカンマ区切り文字列も受け付ける (`_split_cors_origins` バリデータ)。

**コミット禁止**: `.env`、JWT シークレット、fincode キー、カード番号 / CVC / トークン、個人情報。
