# ローカル開発環境構築

React + FastAPI アプリをローカルで起動する手順です。最短コースの説明は [quickstart.md](./quickstart.md) を、環境変数の意味は [../operations/configuration.md](../operations/configuration.md) を参照してください。

## 前提条件

| ツール | バージョン | 備考 |
| --- | --- | --- |
| Python | 3.11+ | `python --version` |
| uv | 最新安定版 | Python依存管理とコマンド実行 |
| Node.js | 22+ | Volta または nvm 推奨 |
| Docker Desktop | 最新安定版 | PostgreSQL とテスト用 testcontainers の実行に必要 |
| PostgreSQL | 16+ | リポジトリ同梱の Docker Compose で起動 |
| fincodeアカウント | テストモード | [fincode-setup.md](./fincode-setup.md) 参照 |

## 1. データベース起動

リポジトリ同梱の Docker Compose で PostgreSQL を起動します。

```bash
docker compose up -d postgres
```

`subscription_app` データベースと `app` ユーザーは初期化時に自動作成されます。テスト用 DB は `testcontainers-python` が pytest 実行時に一時起動するため別途作成は不要です。

## 2. 依存関係インストール

バックエンドとフロントエンドはそれぞれのディレクトリで依存をインストールします。

```bash
# バックエンド
cd backend
uv sync

# フロントエンド
cd ../frontend
npm install
```

バックエンド依存は `backend/pyproject.toml`、フロントエンド依存は `frontend/package.json` で管理します。

## 3. 環境変数

リポジトリ直下の `.env.example` をコピーします。

```bash
cp .env.example .env
```

ローカルで最低限必要な値は `.env.example` のままで動きますが、fincode 連携を試すには次のキーをテスト環境の値に書き換えてください。

```env
FINCODE_API_KEY=m_test_xxxxxxxxxxxxxxxxxxxxxxx
FINCODE_PUBLIC_KEY=p_test_xxxxxxxxxxxxxxxxxxxxxxx
FINCODE_WEBHOOK_SECRET=（fincode 管理画面で発行した署名キー）

# フロントエンドが読み取る公開鍵（同じ値）
VITE_FINCODE_PUBLIC_KEY=p_test_xxxxxxxxxxxxxxxxxxxxxxx
```

全環境変数の意味と既定値は [../operations/configuration.md](../operations/configuration.md) を参照してください。

## 4. マイグレーション

```bash
cd backend
uv run alembic upgrade head
```

新しい migration を取り込んだ後も同じコマンドを実行します。

## 5. アプリ起動

バックエンド（`http://localhost:8000`）:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

フロントエンド（`http://localhost:5173`）:

```bash
cd frontend
npm run dev
```

ブラウザで `http://localhost:5173` を開きます。API ドキュメントは `http://localhost:8000/docs`（Swagger UI）で確認できます。

## よくあるトラブル

| 症状 | 原因の見当 |
| --- | --- |
| 起動時に `sqlalchemy.exc.OperationalError` | `DATABASE_URL` の認証情報またはポートが Docker Compose と不一致 |
| `ModuleNotFoundError` | `cd backend && uv sync` 未実行 |
| ブラウザでCORSエラー | `.env` の `CORS_ORIGINS` と Vite の URL が一致していない |
| JWT付きリクエストが401 | トークン期限切れ、または `JWT_SECRET_KEY` が変わった（localStorage を消して再ログイン） |
| fincodeがunauthorized | APIキーのtest/prodと `FINCODE_BASE_URL` が不一致 |
| pytest で testcontainers が起動しない | Docker Desktop が起動しているか確認 |

## 次に読むもの

- [testing.md](./testing.md) — pytest / Vitest / fincode モック方針
- [fincode-setup.md](./fincode-setup.md) — テストキーとテストカード
- [../architecture/overview.md](../architecture/overview.md) — レイヤ責務とシーケンス図
- [../operations/configuration.md](../operations/configuration.md) — 環境変数リファレンス
