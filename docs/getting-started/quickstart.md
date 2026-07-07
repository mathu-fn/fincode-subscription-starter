# クイックスタート

ローカルで `http://localhost:5173`（フロント）と `http://localhost:8000`（API）を立ち上げ、サブスク機能を一周試すまでの手順です。fincode のテスト環境キーを使って実 API と連携します。

## 前提

- Python 3.11+ と [uv](https://docs.astral.sh/uv/)
- Node.js 22+
- Docker Desktop（PostgreSQL 起動と統合テストの testcontainers で必要）
- fincode テストアカウント（テスト API キーとプランを作成しておく）
- Google OAuth 2.0 クライアント ID（ログインに使用）

## 初回セットアップ

```bash
git clone https://github.com/ltac0203-pixel/fincode-subscription-starter.git
cd fincode-subscription-starter
cp .env.example .env
```

`.env` の fincode 関連キーを fincode 管理画面で発行したテスト環境の値に書き換えます。

```env
FINCODE_API_KEY=m_test_xxxxxxxxxxxxxxxxxxxxxxx
FINCODE_PUBLIC_KEY=p_test_xxxxxxxxxxxxxxxxxxxxxxx
FINCODE_WEBHOOK_SECRET=（fincode 管理画面で発行した署名キー）
```

続いて Google ログイン用のクライアント ID を設定します。[Google Cloud Console](https://console.cloud.google.com/apis/credentials) で「OAuth クライアント ID（ウェブ アプリケーション）」を作成し、「承認済みの JavaScript 生成元」に `http://localhost:5173` を登録してください（リダイレクト URI は不要）。

```env
GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com
VITE_GOOGLE_CLIENT_ID=xxxxxxxx.apps.googleusercontent.com   # バックエンドと同一値
```

## 起動

### ターミナル A：PostgreSQL

```bash
docker compose up -d postgres
```

`subscription_app` データベースと `app` ユーザーが自動作成されます。

### ターミナル B：バックエンド（http://localhost:8000）

```bash
cd backend
uv sync                        # 初回のみ
uv run alembic upgrade head    # 初回 + スキーマ更新時
uv run uvicorn app.main:app --reload
```

- Swagger UI: `http://localhost:8000/docs`

### ターミナル C：フロントエンド（http://localhost:5173）

```bash
cd frontend
npm install                    # 初回のみ
npm run dev
```

### まとめて起動したい場合

```bash
docker compose up
```

postgres / backend / frontend がすべて起動します。

## 画面の流れ

1. **ログイン** — `/login` の「Google でログイン」ボタンで Google アカウントを選択。初回は自動でアカウントが作成されます。
2. **カード追加** — ナビの「カード」で fincode.js のフォームに PAN / 有効期限 / CVC を入力（PAN/CVC はバックエンドに送られません）。fincode のテストカード番号を使ってください。
3. **プラン契約** — ナビの「プラン」→ 支払いカードを選択 → fincode 管理画面で作成済みのプランから選んで契約。
4. **契約の確認・解約** — ナビの「契約」で詳細を確認、「解約する」で次回以降の請求を停止。有料契約は `current_period_end` まで利用できます。
5. **決済履歴** — ナビの「履歴」でページング付きの決済結果一覧。

## Webhook を手動投入する

決済結果は fincode の Webhook から `/api/webhooks/fincode` に通知され、`subscription_results` に書き込まれます。ローカルで動作確認するには次のように手動で投入します。

```bash
# subscription_id は POST /api/subscription のレスポンス fincode_subscription_id
PAYLOAD='{"event_id":"evt_local_1","event":"subscription.payment.succeeded","data":{"subscription_id":"sub_xxxxx","payment_id":"pay_1","amount":"500","status":"succeeded","charged_at":"2026-05-23T12:00:00Z"}}'
SECRET=change-me  # .env の FINCODE_WEBHOOK_SECRET
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

成功すると 204 が返り、「履歴」画面に行が表示されます。本番では fincode 管理画面で `https://YOUR-DOMAIN/api/webhooks/fincode` を送信先に登録します。

## よく使うコマンド

| 用途 | コマンド |
| --- | --- |
| DB だけ起動 | `docker compose up -d postgres` |
| DB 停止 | `docker compose stop postgres` |
| DB の中身を消す | `docker compose down -v` |
| マイグレーション適用 | `cd backend && uv run alembic upgrade head` |
| マイグレーション作成 | `cd backend && uv run alembic revision -m "..."` |
| 1 つ戻す | `cd backend && uv run alembic downgrade -1` |
| バックエンドテスト | `cd backend && uv run pytest` |
| フロントテスト | `cd frontend && npm run test:run` |
| 本番ビルド（フロント） | `cd frontend && npm run build` |
| OpenAPI 検証 | `npx @redocly/cli lint docs/api/openapi.yml` |
| Swagger UI | `http://localhost:8000/docs` |

## トラブルシュート

| 症状 | 確認ポイント |
| --- | --- |
| `sqlalchemy.exc.OperationalError` で起動失敗 | `docker compose ps` で postgres が `(healthy)` か。`.env` の `DATABASE_URL` のポート / パスワードが Compose と一致するか |
| `ModuleNotFoundError` | `cd backend && uv sync` 未実行 |
| ブラウザで CORS エラー | `.env` の `CORS_ORIGINS` と `VITE_API_BASE_URL` が一致しているか |
| ログイン後すぐ 401 | `JWT_SECRET_KEY` を変えたら既存トークンは無効。ブラウザの localStorage をクリアして再ログイン |
| Google ログインが 401 `invalid_google_token` | `GOOGLE_CLIENT_ID`（バックエンド）と `VITE_GOOGLE_CLIENT_ID`（フロント）が同一値か確認 |
| Google ボタンが表示されない | Google Cloud Console の「承認済みの JavaScript 生成元」に `http://localhost:5173` が登録されているか確認 |
| fincode の API キーが unauthorized | テスト環境キー（`m_test_*` / `p_test_*`）と `https://api.test.fincode.jp` の組み合わせか確認 |
| pytest で testcontainers が起動しない | Docker Desktop が起動しているか確認 |

## 次に読むもの

- [ローカル開発](./local-development.md) — 詳細な開発手順
- [Fincodeセットアップ](./fincode-setup.md) — 実 API キー取得とテストカード
- [API 仕様](../api/README.md) — エンドポイント一覧とエラー形式
- [アーキテクチャ概要](../architecture/overview.md) — レイヤ責務とシーケンス図
- [Webhook 統合](../customization/webhooks.md) — 署名検証と冪等性
