# 環境変数リファレンス

`.env` で設定するすべての環境変数の意味、既定値、設定例をまとめます。バックエンドは `backend/app/core/config.py` の `Settings`（pydantic-settings）が `.env` を読み取り、フロントエンドは Vite が `VITE_*` キーをビルド時に取り込みます。

リポジトリ直下の `.env.example` が雛形です。

```bash
cp .env.example .env
```

## アプリケーション

| キー | 既定値 | 用途 |
| --- | --- | --- |
| `APP_ENV` | `local` | 実行環境ラベル。`local` / `staging` / `production` などを設定 |
| `APP_URL` | `http://localhost:5173` | フロントエンドの公開 URL（メール本文等に使う場合の参照） |
| `API_URL` | `http://localhost:8000` | バックエンドの公開 URL |

## データベース

| キー | 既定値 | 用途 |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://app:change-me@127.0.0.1:5432/subscription_app` | SQLAlchemy 非同期接続 URL。Alembic は内部で `+asyncpg` を `+psycopg` に置換した同期 URL を使う |

> Docker Compose で立てた PostgreSQL の認証情報（`app` / `change-me`）と一致させてください。本番では secret store から渡します。

## 認証 (Google ログイン + JWT)

| キー | 既定値 | 用途 |
| --- | --- | --- |
| `GOOGLE_CLIENT_ID` | （空） | Google OAuth 2.0 クライアント ID。GIS が発行する ID トークンの `aud` 検証に使う。本番では必須。フロントの `VITE_GOOGLE_CLIENT_ID` と**同一値**にする（食い違うと全ログインが 401 になる） |
| `JWT_SECRET_KEY` | `change-this-in-production` | JWT 署名鍵。本番では 32 バイト以上のランダム値を必須 |
| `JWT_ALGORITHM` | `HS256` | 署名アルゴリズム |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | アクセストークン有効期限（分） |

`GOOGLE_CLIENT_ID` は [Google Cloud Console](https://console.cloud.google.com/apis/credentials) で「OAuth クライアント ID（ウェブ アプリケーション）」を作成して取得します。「承認済みの JavaScript 生成元」にフロントエンドのオリジン（ローカルなら `http://localhost:5173`）を登録してください。リダイレクト URI は不要です（GIS のボタンフローを使用）。

`JWT_SECRET_KEY` を変更すると既存トークンは全て無効になります（複数検証鍵をサポートしていないため）。運用方針は [api-token-rotation.md](./api-token-rotation.md) を参照。

## fincode

| キー | 既定値 | 用途 |
| --- | --- | --- |
| `FINCODE_MODE` | `live` | `mock` にすると fincode API を一切叩かず固定のダミーデータを返す（fincode アカウント不要の開発用）。本番では `live` のままにする。`.env.example` は手早く試せるよう `mock` 入りで配布している |
| `FINCODE_API_KEY` | （空） | fincode シークレットキー（`m_test_*` / `m_prod_*`）。バックエンドから fincode API を呼び出すのに使う。`FINCODE_MODE=mock` のときは未設定でよい |
| `FINCODE_PUBLIC_KEY` | （空） | fincode 公開鍵（`p_test_*` / `p_prod_*`）。サーバ側参照用 |
| `FINCODE_BASE_URL` | `https://api.test.fincode.jp` | fincode API のエンドポイント。本番は `https://api.fincode.jp` |
| `FINCODE_TENANT_SHOP_ID` | （空） | プラットフォーム / マルチテナント構成のみ必要。設定すると `Tenant-Shop-Id` ヘッダーが送信される |
| `FINCODE_WEBHOOK_SECRET` | `change-me` | fincode Webhook 署名検証（HMAC-SHA256）の鍵 |

シークレットキー / 公開鍵 / ベース URL の組み合わせはテスト / 本番で揃える必要があります（`m_test_*` と `https://api.test.fincode.jp`、`m_prod_*` と `https://api.fincode.jp`）。

## CORS

| キー | 既定値 | 用途 |
| --- | --- | --- |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | 許可するオリジン（カンマ区切り文字列）。本番では公開ドメインを明示し、wildcard は使わない |

## レート制限

| キー | 既定値 | 用途 |
| --- | --- | --- |
| `RATE_LIMIT_STORAGE_URI` | `memory://` | slowapi のストレージ URI。複数ワーカー構成では Redis（例: `redis://localhost:6379/0`）を推奨 |

未認証エンドポイント（`/api/auth/google` など）のレート制限はクライアント IP をキーにします。リバースプロキシ / ロードバランサー配下では、uvicorn に `--proxy-headers --forwarded-allow-ips=<信頼するプロキシのIP>` を付けて `X-Forwarded-For` を解決してください。これを怠ると全リクエストがプロキシの IP に見え、未認証の制限（例: ログイン 5 回/分）が全ユーザー合算になりログインを妨害します。

## フロントエンド (Vite)

これらは `frontend/` のビルド時に Vite が読み取ります。`VITE_` プレフィックス付きの値はビルド成果物に埋め込まれるため、シークレットを入れないでください。

| キー | 既定値 | 用途 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | フロントエンドが呼び出すバックエンドのベース URL |
| `VITE_GOOGLE_CLIENT_ID` | （空） | GIS のログインボタンに使う Google OAuth 2.0 クライアント ID。バックエンドの `GOOGLE_CLIENT_ID` と**同一値** |
| `VITE_FINCODE_MODE` | （空 = ライブ） | `mock` にするとフロントは fincode.js を読み込まず、カード登録フォームがテストトークン直接入力に切り替わる。バックエンドの `FINCODE_MODE` と揃える |
| `VITE_FINCODE_PUBLIC_KEY` | （空） | ブラウザ上の fincode.js で使う公開鍵。`FINCODE_PUBLIC_KEY` と同じ値。`VITE_FINCODE_MODE=mock` のときは不要 |
| `VITE_FINCODE_SDK_URL` | `https://js.test.fincode.jp/v1/fincode.js` | 読み込む fincode.js SDK の URL。本番は `https://js.fincode.jp/v1/fincode.js` |

## 環境ごとの典型値

### ローカル開発

```env
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://app:change-me@127.0.0.1:5432/subscription_app
JWT_SECRET_KEY=change-this-in-production-please-use-32+-random-bytes
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
FINCODE_API_KEY=m_test_xxxxxxxxxxxxxxxxxxxxxxx
FINCODE_PUBLIC_KEY=p_test_xxxxxxxxxxxxxxxxxxxxxxx
FINCODE_BASE_URL=https://api.test.fincode.jp
FINCODE_WEBHOOK_SECRET=local-webhook-secret
CORS_ORIGINS=http://localhost:5173
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
VITE_FINCODE_PUBLIC_KEY=p_test_xxxxxxxxxxxxxxxxxxxxxxx
VITE_FINCODE_SDK_URL=https://js.test.fincode.jp/v1/fincode.js
```

### 本番

```env
APP_ENV=production
APP_URL=https://app.example.com
API_URL=https://api.example.com
DATABASE_URL=postgresql+asyncpg://app:<strong-password>@db.internal:5432/subscription_app
JWT_SECRET_KEY=<32+ bytes of randomness from secret store>
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
ACCESS_TOKEN_EXPIRE_MINUTES=30
FINCODE_MODE=live
FINCODE_API_KEY=m_prod_xxxxxxxxxxxxxxxxxxxxxxx
FINCODE_PUBLIC_KEY=p_prod_xxxxxxxxxxxxxxxxxxxxxxx
FINCODE_BASE_URL=https://api.fincode.jp
FINCODE_WEBHOOK_SECRET=<from fincode dashboard>
CORS_ORIGINS=https://app.example.com
RATE_LIMIT_STORAGE_URI=redis://redis.internal:6379/0
VITE_API_BASE_URL=https://api.example.com
VITE_GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
VITE_FINCODE_PUBLIC_KEY=p_prod_xxxxxxxxxxxxxxxxxxxxxxx
VITE_FINCODE_SDK_URL=https://js.fincode.jp/v1/fincode.js
```

## 秘密情報の扱い

- `.env` および本番用の値はリポジトリにコミットしない。`.gitignore` で除外済み
- fincode シークレットキー、JWT 署名鍵、DB パスワード、Webhook シークレットは secret store（AWS Secrets Manager、HashiCorp Vault、SOPS など）から渡す
- ログに環境変数の値を出力しない（カード情報・JWT・API キーのマスクはアプリ側でも徹底）
