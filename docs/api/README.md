# docs/api — API仕様書

## ファイル一覧

| ファイル | 説明 |
| --- | --- |
| [openapi.yml](./openapi.yml) | 本アプリ REST API の OpenAPI 3.0.3 仕様 |

`openapi.yml` は本アプリが公開するAPIの仕様です。fincode APIそのものの仕様ではありません。カードトークン化以外の fincode API 呼び出しは FastAPI サーバー側で行います。

## 認証方式

API は **JWT Bearer認証** を使います。

```http
POST /api/login
Content-Type: application/json

{ "email": "user@example.com", "password": "password123" }
```

レスポンス:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_at": "2026-05-23T12:00:00Z",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "テストユーザー"
  }
}
```

認証が必要なリクエスト:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

React アプリは認証レイヤーでトークンを保持し、API 呼び出し時にヘッダーへ付与します。ブラウザのストレージにトークンを保存する fork では、XSS 対策を本番リリースの必須条件にしてください。

## エンドポイント早見表

| メソッド | パス | 認証 | レート制限 | 説明 |
| --- | --- | --- | --- | --- |
| POST | `/api/register` | 不要 | 5回/分 | ユーザー登録 |
| POST | `/api/login` | 不要 | 5回/分 | ログインとJWT発行 |
| GET | `/api/session-status` | 必須 | 60回/分 | 認証状態確認 |
| POST | `/api/logout` | 必須 | 60回/分 | 現在のトークンを失効扱いにする |
| GET | `/api/user` | 必須 | 60回/分 | 認証ユーザー情報取得 |
| GET | `/api/subscription` | 必須 | 60回/分 | アクティブなサブスクリプション取得 |
| POST | `/api/subscription` | 必須 | 3回/分 | サブスクリプション登録 |
| PATCH | `/api/subscription` | 必須 | 5回/分 | アクティブなサブスクリプションのプラン変更 |
| DELETE | `/api/subscription` | 必須 | 5回/分 | サブスクリプション解約 |
| GET | `/api/subscription/history` | 必須 | 60回/分 | 決済履歴取得 |
| GET | `/api/subscription/plans` | 必須 | 60回/分 | fincodeの有効プラン一覧取得 |
| GET | `/api/subscription/cards` | 必須 | 60回/分 | 登録済みカード一覧取得 |
| POST | `/api/subscription/cards` | 必須 | 3回/分 | fincodeトークンからカード登録 |
| DELETE | `/api/subscription/cards/{card_id}` | 必須 | 5回/分 | カード削除 |
| POST | `/api/webhooks/fincode` | 署名 | 120回/分 | fincode webhook受信 |

## エラー形式

FastAPI/Pydantic のバリデーションエラーは標準の `detail` 配列を返します。

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error"
    }
  ]
}
```

アプリケーションエラーは安定したコードとメッセージを返します。

```json
{
  "detail": {
    "code": "active_subscription_exists",
    "message": "このユーザーには既にアクティブな契約があります。"
  }
}
```

| ステータス | 意味 |
| --- | --- |
| 401 | JWTなし、期限切れ、不正 |
| 403 | 認証済みだが対象リソースを操作できない |
| 404 | リソースなし |
| 409 | 状態競合 |
| 422 | 入力または業務ルールのエラー |
| 429 | レート制限 |
| 502/503/504 | fincode または決済サービス連携失敗 |

## Fincode APIとの関係

```text
Reactフロントエンド
  |
  |-- カード入力 -> fincode.jsでトークン化
  |
  `-- 本アプリ REST API
        |
        `-- FastAPIサービス
              |
              `-- fincode API
                    |-- CustomerService
                    |-- CardService
                    |-- PlanService
                    `-- SubscriptionService
```

フロントエンドが fincode を直接呼び出すのはカードトークン化だけです。それ以外の fincode API 操作はサーバーサイドで行います。

## プレビューと検証

```bash
npx @redocly/cli preview-docs docs/api/openapi.yml
npx @redocly/cli lint docs/api/openapi.yml
```
