<div align="center">

# fincode Subscription Starter

**fincode の定期課金を、プロダクション水準で取り込む。**

React + FastAPI で書かれた fincode 定期課金の OSS リファレンス実装です。
カードのトークン化、サブスクリプション登録・解約、Webhook の冪等処理、監査ログまで、
そのまま自社サービスに取り込める形で提供します。

[![CI](https://github.com/ltac0203-pixel/fincode-subscription-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/ltac0203-pixel/fincode-subscription-starter/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node 22+](https://img.shields.io/badge/node-22+-brightgreen.svg)](https://nodejs.org/)
[![fincode](https://img.shields.io/badge/fincode-定期課金-0ea5e9.svg)](https://www.fincode.jp/)

</div>

---

## なぜこのリファレンス実装か

| | |
| --- | --- |
| **PAN / CVC はサーバーに来ない** | ブラウザ上の fincode.js でトークン化し、REST にはカードトークンのみ送信。バックエンドはカード番号や CVC を一度も保持しません。PCI DSS の影響範囲を最小化する設計です。 |
| **本番想定の堅牢な実装** | fincode 書き込みの Idempotency-Key 再利用、5xx / タイムアウト時のリトライ、Circuit Breaker、partial unique index による「1 ユーザー 1 アクティブ契約」の DB 保証など、エッジケースに最初から備えています。 |
| **自社サービスに移植しやすい** | fincode 直接呼び出しは `app/services/fincode/` に閉じ込め、Manager 層と REST 層の責務が厳格に分かれています。ドメインロジックの切り出しが容易な構成です。 |

---

## 含まれている機能

- **ユーザー登録 / JWT 認証** — pwdlib (argon2) によるパスワードハッシュと JWT Bearer。`/api/register` と `/api/login` を最小構成で提供
- **カードトークン化** — fincode.js の UI コンポーネントを React に組み込み、PAN / CVC をバックエンドに送らずトークンのみを REST に渡す
- **プラン表示と契約登録** — fincode から契約可能なプラン一覧を取得し、契約時には `plan_snapshot` を JSONB で永続化して履歴の意味を保つ
- **解約フロー** — fincode に即時解約要求 → ローカル `status` を `cancelled` に更新。期間末までのアクセス可否は業務側で判断
- **Webhook 受信と冪等性** — `Fincode-Signature` の HMAC-SHA256 検証 + `webhook_events_seen` と `subscription_results` upsert の二段冪等で再送に強い
- **決済履歴 / ページング** — `subscription_results` に 1 課金 1 行で書き込まれた決済結果を、フロントからページング付きで参照
- **監査ログ** — 成功した業務操作は `audit_logs` に before / after JSONB で記録、失敗は構造化ログにのみ残し PII 漏洩を避ける
- **カード soft delete** — `fincode_cards.deleted_at` で論理削除。過去契約と監査ログの説明可能性を維持し、誤削除からの復旧余地を残す
- **OpenAPI 仕様** — 公開 API は `docs/api/openapi.yml` に定義し、Redocly で lint 通過済み。クライアント自動生成にもそのまま使える

---

## 技術スタック

| レイヤ | 技術 |
| --- | --- |
| フロントエンド | React + Vite + TypeScript + Tailwind CSS v4 |
| バックエンド | FastAPI + Python 3.11+ (uv) |
| API スキーマ | Pydantic v2 / OpenAPI 3.1 |
| データベース | PostgreSQL 16+ |
| ORM / マイグレーション | SQLAlchemy 2.x (async) + Alembic |
| 認証 | JWT Bearer + pwdlib (argon2) |
| 決済 | fincode 定期課金 |
| テスト | pytest + testcontainers + Vitest |

---

## アーキテクチャ

```text
React UI (frontend/src/)
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
FincodeHttpClient → fincode API
```

逆方向の参照は禁止。fincode への HTTP 呼び出しは fincode サービス層に集中し、API ルートや Manager 層から直接 `httpx` を叩くことはありません。詳細は [docs/architecture/overview.md](./docs/architecture/overview.md) を参照。

---

## クイックスタート

### 必要なもの

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node.js 22+
- Docker Desktop（PostgreSQL を Docker Compose で起動するため）
- fincode テストアカウント（テスト API キーとプラン作成が必要）

### 1. リポジトリ取得と環境変数

```bash
git clone https://github.com/ltac0203-pixel/fincode-subscription-starter.git
cd fincode-subscription-starter
cp .env.example .env
```

`.env` の `FINCODE_API_KEY` / `FINCODE_PUBLIC_KEY` / `FINCODE_WEBHOOK_SECRET` に fincode 管理画面で発行したテスト環境のキーを設定してください。詳細は [docs/getting-started/fincode-setup.md](./docs/getting-started/fincode-setup.md)。

> テスト用 fincode キー（`m_test_*` / `p_test_*`）と `https://api.test.fincode.jp` の組み合わせで、すぐ動かせます。

### 2. 起動コマンド（推奨：3 ターミナル）

<details open>
<summary><strong>ターミナル A — PostgreSQL</strong></summary>

```bash
docker compose up -d postgres
```

`subscription_app` データベースと `app` ユーザーが自動作成されます。`docker compose ps` で `(healthy)` を確認できます。

</details>

<details open>
<summary><strong>ターミナル B — バックエンド (FastAPI, http://localhost:8000)</strong></summary>

```bash
cd backend
uv sync                        # 初回のみ依存をインストール
uv run alembic upgrade head    # マイグレーション適用（初回 + スキーマ更新時）
uv run uvicorn app.main:app --reload
```

`http://localhost:8000/docs` で Swagger UI、`http://localhost:8000/health` でヘルスチェックを確認できます。

</details>

<details open>
<summary><strong>ターミナル C — フロントエンド (Vite, http://localhost:5173)</strong></summary>

```bash
cd frontend
npm install                    # 初回のみ
npm run dev
```

ブラウザで `http://localhost:5173` を開きます。

</details>

#### まとめて起動（Docker Compose）

```bash
docker compose up
```

postgres / backend / frontend がすべて起動し、`http://localhost:5173` と `http://localhost:8000` がそのまま使えます。

### 3. 画面の流れ

事前に fincode 管理画面で課金プランを作成しておく必要があります（テスト環境で問題ありません）。

1. **新規登録** — `http://localhost:5173/register` で名前 / メール / パスワード（8 文字以上）を入力。登録後は自動でログイン状態になります。
2. **カード追加** — ナビの「カード」を開くと fincode.js のフォームで PAN / 有効期限 / CVC を入力（PAN / CVC はサーバーへ送られません）。fincode のテストカード番号を使ってください。
3. **プラン契約** — ナビの「プラン」→ 支払いカードを選択 → fincode で作成済みのプランから選び「このプランを契約」。
4. **契約の確認・解約** — ナビの「契約」で詳細表示。`解約する` を押すと `status=cancelled` に切り替わります（fincode へ解約要求も飛びます）。
5. **決済履歴** — ナビの「履歴」でページングされた決済結果を表示。Webhook で `subscription_results` に書き込まれた行が出ます。

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

---

## よく使うコマンド

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

---

## うまく動かないとき

| 症状 | 確認 |
| --- | --- |
| `sqlalchemy.exc.OperationalError` で起動失敗 | `docker compose ps` で postgres が `(healthy)` か確認。`.env` の `DATABASE_URL` のポート / パスワードが Compose と一致するか |
| `ModuleNotFoundError` | `cd backend && uv sync` を実行 |
| フロントが API に繋がらない | `.env` の `VITE_API_BASE_URL` と `cors_origins` がブラウザの URL と一致しているか |
| ログイン後すぐ 401 | `JWT_SECRET_KEY` を変えたら既存トークンは無効。ブラウザの localStorage をクリアして再ログイン |
| fincode の API キーが unauthorized | テスト環境キー（`m_test_*` / `p_test_*`）と `https://api.test.fincode.jp` の組み合わせか確認 |

---

## 設計上の注意点

### 解約ポリシー

`DELETE /api/subscription` は fincode へ即時解約を要求し、ローカル `subscriptions.status` を `cancelled` へ、`cancelled_at` を `now()` へ更新します。請求期間末（`current_period_end`）までのアクセス可否はアプリの業務判断で、Webhook 受信時に `subscription_results` と `status` が更新されます。

### JWT の保管について

フロントエンドは JWT を `localStorage` に保存します。XSS 経由でトークンを盗まれない設計（Content Security Policy、依存ライブラリの監査、`dangerouslySetInnerHTML` の禁止、ストアド XSS テスト）を本番投入条件にしてください。

---

## API

公開 API は [docs/api/openapi.yml](./docs/api/openapi.yml) に定義します。認証が必要なエンドポイントは次のヘッダーを使います。

```http
Authorization: Bearer <jwt>
```

React フロントエンドが fincode を直接呼び出すのはカードトークン化だけです。それ以外の fincode API 操作は FastAPI のサーバーサイドサービスから実行します。

---

## ディレクトリ構成

```text
app/                  FastAPI バックエンド
app/api/              API router と dependency
app/core/             設定、セキュリティ、ログ
app/models/           SQLAlchemy model
app/schemas/          Pydantic request/response schema
app/services/         subscription / card / customer / fincode サービス
alembic/              DB マイグレーション
frontend/src/         React アプリ
docs/                 ドキュメント
tests/                pytest テスト
```

---

## テスト

```bash
cd backend && uv run pytest --cov=app
cd ../frontend && npm run test:run
npx @redocly/cli lint docs/api/openapi.yml
```

自動テストでは fincode API を直接呼び出さず、サーバーサイドの fincode クライアントをモックします。バックエンドの統合テストは `testcontainers-python` で PostgreSQL を立ち上げるため、Docker が起動している必要があります。

---

## ドキュメント

[docs/README.md](./docs/README.md) から読み始めてください。

- [ローカル開発](./docs/getting-started/local-development.md)
- [Fincode セットアップ](./docs/getting-started/fincode-setup.md)
- [API 仕様](./docs/api/README.md)
- [アーキテクチャ概要](./docs/architecture/overview.md)
- [環境変数リファレンス](./docs/operations/configuration.md)
- [本番デプロイ](./docs/operations/deployment.md)

---

## セキュリティ

カード番号、CVC、fincode トークン、JWT、API キー、個人情報をログに出さないでください。脆弱性は **公開 Issue ではなく**、GitHub の Private Vulnerability Reporting で非公開に報告してください。手順は [SECURITY.md](./SECURITY.md) を参照。

---

## コントリビュート

Issue / Pull Request 歓迎です。最初に次のドキュメントを読んでください。

- [CONTRIBUTING.md](./CONTRIBUTING.md) — 開発フロー、コミット規約、PR チェックリスト
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) — 行動規範（Contributor Covenant v2.1）
- [SECURITY.md](./SECURITY.md) — 脆弱性報告手順
- [AGENTS.md](./AGENTS.md) — コントリビューター向け詳細ガイド（コーディング規約・テスト方針）

---

## ライセンス

[Apache License, Version 2.0](./LICENSE)。コントリビュートは同ライセンス下で配布されることに同意したものとみなされます。

> fincode は GMO Payment Gateway 株式会社の決済サービスです。本プロジェクトは fincode を利用するための非公式リファレンス実装であり、GMO Payment Gateway 社による公式提供物ではありません。
