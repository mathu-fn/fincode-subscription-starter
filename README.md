# fincode Subscription Starter

[![CI](https://github.com/ltac0203-pixel/fincode-subscription-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/ltac0203-pixel/fincode-subscription-starter/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node 22+](https://img.shields.io/badge/node-22+-brightgreen.svg)](https://nodejs.org/)

**React + FastAPI** と **fincode** の定期課金を使って、Webアプリ向けサブスクリプション機能を実装するためのOSSリファレンスです。

カード登録、サブスクリプション登録、解約、決済履歴、監査ログを、自社サービスへ取り込める形で提供することを目的にしています。

## 主な機能

- ユーザー登録と JWT Bearer 認証
- fincode からの契約可能プラン取得
- fincode.js によるカードトークン化
- カード登録・削除
- サブスクリプション登録・解約
- 決済履歴
- カード操作・契約操作の監査ログ
- Fincode Webhook 連携の設計指針

カード番号とCVCは FastAPI バックエンドに送信しません。ブラウザ上の fincode.js でトークン化し、REST API にはカードトークンのみを送信します。

## 技術スタック

| レイヤ | 技術 |
| --- | --- |
| フロントエンド | React + Vite + TypeScript |
| バックエンド | FastAPI + Python |
| APIスキーマ | Pydantic |
| データベース | PostgreSQL 16+ |
| ORM / マイグレーション | SQLAlchemy 2.x (async) + Alembic |
| 認証 | JWT Bearer |
| 決済 | fincode 定期課金 |
| テスト | pytest + Vitest |
| Pythonツール | uv |

## クイックスタート

### 必要なもの

- Python 3.11+
- uv
- Node.js 22+
- Docker Desktop（PostgreSQL を Docker Compose で起動するため）
- fincode テストアカウント（テスト API キーとプラン作成が必要）

### 1. リポジトリ取得と環境変数

```bash
git clone https://github.com/ltac0203-pixel/fincode-subscription-starter.git
cd fincode-subscription-starter
cp .env.example .env
```

`.env` の `FINCODE_API_KEY` / `FINCODE_PUBLIC_KEY` / `FINCODE_WEBHOOK_SECRET` に fincode 管理画面で発行したテスト環境のキーを設定してください。詳細は [docs/getting-started/fincode-setup.md](./docs/getting-started/fincode-setup.md) を参照。

### 2. 起動コマンド（推奨：3ターミナル）

#### ターミナル A — PostgreSQL

```bash
docker compose up -d postgres
```

`subscription_app` データベースと `app` ユーザーが自動作成されます。`docker compose ps` で `(healthy)` を確認できます。

#### ターミナル B — バックエンド（FastAPI、http://localhost:8000）

```bash
cd backend
uv sync                        # 初回のみ依存をインストール
uv run alembic upgrade head    # マイグレーション適用（初回 + スキーマ更新時）
uv run uvicorn app.main:app --reload
```

`http://localhost:8000/docs` で Swagger UI、`http://localhost:8000/health` でヘルスチェックを確認できます。

#### ターミナル C — フロントエンド（Vite、http://localhost:5173）

```bash
cd frontend
npm install                    # 初回のみ
npm run dev
```

ブラウザで `http://localhost:5173` を開きます。

#### まとめて起動（Docker Compose）

```bash
docker compose up
```

postgres / backend / frontend がすべて起動し、`http://localhost:5173` と `http://localhost:8000` がそのまま使えます。

### 3. 使い方（画面の流れ）

事前に fincode 管理画面で課金プランを作成しておく必要があります（テスト環境で問題ありません）。

1. **新規登録** — `http://localhost:5173/register` を開き、名前 / メール / パスワード（8文字以上）を入力して登録。登録後は自動でログイン状態になります。
2. **カード追加** — ナビの「カード」を開くと fincode.js のフォームで PAN / 有効期限 / CVC を入力します（PAN/CVC はサーバーへ送られません）。fincode のテストカード番号を使ってください。
3. **プラン契約** — ナビの「プラン」→ 支払いカードを選択 → fincode で作成済みのプランから選んで「このプランを契約」を押すと契約完了。
4. **契約の確認・解約** — ナビの「契約」で詳細表示。`解約する` を押すと `status=cancelled` に切り替わります（fincode へ解約要求も飛びます）。
5. **決済履歴** — ナビの「履歴」でページングされた決済結果を表示。履歴は fincode の Webhook で `subscription_results` に書き込まれた行が出ます（下記「Webhook の確認」参照）。

### 4. Webhook の確認（任意）

決済結果はバックエンドが受信する Webhook に依存します。ローカルで手動投入する例:

```bash
# subscription_id は POST /api/subscription のレスポンス fincode_subscription_id を使う
PAYLOAD='{"event_id":"evt_local_1","event":"subscription.payment.succeeded","data":{"subscription_id":"sub_xxxxx","payment_id":"pay_1","amount":"500","status":"succeeded","charged_at":"2026-05-23T12:00:00Z"}}'
SECRET=change-me   # .env の FINCODE_WEBHOOK_SECRET
SIG=$(printf "%s" "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $2}')

curl -X POST http://localhost:8000/api/webhooks/fincode \
  -H "Content-Type: application/json" \
  -H "Fincode-Signature: $SIG" \
  -d "$PAYLOAD"
```

PowerShell の例:

```powershell
$payload = '{"event_id":"evt_local_1","event":"subscription.payment.succeeded","data":{"subscription_id":"sub_xxxxx","payment_id":"pay_1","amount":"500","status":"succeeded","charged_at":"2026-05-23T12:00:00Z"}}'
$secret  = 'change-me'
$hmac    = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($secret)
$sig     = ($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($payload)) | ForEach-Object { $_.ToString('x2') }) -join ''
Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/webhooks/fincode' `
  -ContentType 'application/json' `
  -Headers @{ 'Fincode-Signature' = $sig } `
  -Body $payload
```

成功すると 204、フロントの「履歴」画面に行が出ます。本番では fincode 管理画面で `https://YOUR-DOMAIN/api/webhooks/fincode` を Webhook 送信先に登録してください。

### 5. よく使うコマンド

| 用途 | コマンド |
| --- | --- |
| DB だけ起動 | `docker compose up -d postgres` |
| DB 停止 | `docker compose stop postgres` |
| DB の中身をリセット | `docker compose down -v` |
| マイグレーション適用 | `cd backend && uv run alembic upgrade head` |
| マイグレーション作成 | `cd backend && uv run alembic revision -m "メッセージ"` |
| 1 つ戻す | `cd backend && uv run alembic downgrade -1` |
| バックエンドだけ再起動 | Ctrl-C 後 `uv run uvicorn app.main:app --reload` |
| バックエンドのテスト | `cd backend && uv run pytest` |
| フロントのテスト | `cd frontend && npm run test:run` |
| OpenAPI 仕様の検証 | `npx @redocly/cli lint docs/api/openapi.yml` |
| 本番ビルド（フロント） | `cd frontend && npm run build` |
| API 仕様ブラウズ | `http://localhost:8000/docs`（Swagger UI） |

### 6. うまく動かないとき

| 症状 | 確認 |
| --- | --- |
| `sqlalchemy.exc.OperationalError` で起動失敗 | `docker compose ps` で postgres が `(healthy)` か確認。`.env` の `DATABASE_URL` のポート / パスワードが Compose と一致するか |
| `ModuleNotFoundError` | `cd backend && uv sync` を実行 |
| フロントが API に繋がらない | `.env` の `VITE_API_BASE_URL` と `cors_origins` がブラウザの URL と一致しているか |
| ログイン後すぐ 401 | `JWT_SECRET_KEY` を変えたら既存トークンは無効。ブラウザの localStorage をクリアして再ログイン |
| fincode の API キーが unauthorized | テスト環境キー（`m_test_*` / `p_test_*`）と `https://api.test.fincode.jp` の組み合わせか確認 |

### 解約ポリシー

`DELETE /api/subscription` は fincode へ即時解約を要求し、ローカル `subscriptions.status` を `cancelled` へ、`cancelled_at` を `now()` へ更新します。請求期間末（`current_period_end`）までのアクセス可否はアプリの業務判断で、Webhook 受信時に `subscription_results` と `status` が更新されます。

### JWT の保管について

フロントエンドは JWT を `localStorage` に保存します。XSS 経由でトークンを盗まれない設計（Content Security Policy、依存ライブラリの監査、`dangerouslySetInnerHTML` の禁止、ストアド XSS テスト）を本番投入条件にしてください。

## API

公開APIは [docs/api/openapi.yml](./docs/api/openapi.yml) に定義します。認証が必要なエンドポイントは次のヘッダーを使います。

```http
Authorization: Bearer <jwt>
```

React フロントエンドが fincode を直接呼び出すのはカードトークン化だけです。それ以外の fincode API 操作は FastAPI のサーバーサイドサービスから実行します。

## ディレクトリ構成

```text
app/                  FastAPI バックエンド
app/api/              API router と dependency
app/core/             設定、セキュリティ、ログ
app/models/           SQLAlchemy model
app/schemas/          Pydantic request/response schema
app/services/         subscription/card/customer/fincode サービス
alembic/              DBマイグレーション
frontend/src/         React アプリ
docs/                 ドキュメント
tests/                pytest テスト
```

## テスト

```bash
cd backend && uv run pytest --cov=app
cd ../frontend && npm run test:run
npx @redocly/cli lint docs/api/openapi.yml
```

自動テストでは fincode API を直接呼び出さず、サーバーサイドの fincode クライアントをモックします。バックエンドの統合テストは `testcontainers-python` で PostgreSQL を立ち上げるため、Docker が起動している必要があります。

## ドキュメント

[docs/README.md](./docs/README.md) から読み始めてください。

- [ローカル開発](./docs/getting-started/local-development.md)
- [Fincodeセットアップ](./docs/getting-started/fincode-setup.md)
- [API仕様](./docs/api/README.md)
- [アーキテクチャ概要](./docs/architecture/overview.md)
- [環境変数リファレンス](./docs/operations/configuration.md)
- [本番デプロイ](./docs/operations/deployment.md)

## セキュリティ

カード番号、CVC、fincodeトークン、JWT、APIキー、個人情報をログに出さないでください。脆弱性は **公開 Issue ではなく**、GitHub の Private Vulnerability Reporting で非公開に報告してください。手順は [SECURITY.md](./SECURITY.md) を参照。

## コントリビュート

Issue / Pull Request 歓迎です。最初に次のドキュメントを読んでください。

- [CONTRIBUTING.md](./CONTRIBUTING.md) — 開発フロー、コミット規約、PR チェックリスト
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) — 行動規範（Contributor Covenant v2.1）
- [SECURITY.md](./SECURITY.md) — 脆弱性報告手順
- [AGENTS.md](./AGENTS.md) — コントリビューター向け詳細ガイド（コーディング規約・テスト方針）

## ライセンス

[Apache License, Version 2.0](./LICENSE)。コントリビュートは同ライセンス下で配布されることに同意したものとみなされます。
