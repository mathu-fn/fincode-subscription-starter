# 本番デプロイ

Nginx、Uvicorn、PostgreSQL 16+、systemd などのプロセスマネージャを使った、Linux でのセルフホスト環境の参考手順です。

## チェックリスト

| 項目 | 必須 | 補足 |
| --- | --- | --- |
| `APP_ENV=production` | 必須 | 開発用の挙動を無効化する |
| `APP_URL` / `API_URL` | 必須 | 公開する origin と一致させる |
| `DATABASE_URL` | 必須 | 本番 DB の認証情報は secret store から渡す |
| `JWT_SECRET_KEY` | 必須 | 強いランダム値。計画的にローテーションする |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 必須 | 想定するリスクに合わせて短めに設定する |
| `FINCODE_API_KEY=m_prod_...` | 必須 | 本番の secret key |
| `FINCODE_PUBLIC_KEY=p_prod_...` | 必須 | ブラウザでのトークン化に使う公開鍵 |
| `FINCODE_BASE_URL=https://api.fincode.jp` | 必須 | 本番 fincode のエンドポイント |
| `FINCODE_WEBHOOK_SECRET` | 必須 | Webhook を使う場合 |
| HTTPS | 必須 | 認証と決済 UX に必須 |
| 構造化ログ | 推奨 | CloudWatch、Datadog、Loki などへ集約する |

## ビルド

```bash
git fetch --all
git checkout <release-tag-or-sha>

uv sync --frozen --no-dev
npm ci
npm run build

uv run alembic upgrade head
```

フロントエンドのビルド成果物は、Nginx、CDN、同じホスト上など、デプロイ構成に応じて配信します。

## Uvicornサービス

systemd unit の例:

```ini
[Unit]
Description=fincode subscription FastAPI
After=network.target

[Service]
WorkingDirectory=/var/www/fincode-subscription
EnvironmentFile=/etc/fincode-subscription.env
ExecStart=/usr/local/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

トラフィックが増える場合は、Gunicorn 経由で Uvicorn worker を起動します。

```bash
uv run gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 127.0.0.1:8000
```

## Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name app.example.com;

    root /var/www/fincode-subscription/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri /index.html;
    }

    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### セキュリティヘッダと `/metrics`

- バックエンドは全レスポンスに `X-Content-Type-Options: nosniff` / `X-Frame-Options: DENY` / `Referrer-Policy: no-referrer` を付与します（`app/core/middleware.py` の `SecurityHeadersMiddleware`）。SPA 本体を保護する `Content-Security-Policy` は fincode.js / Google GIS の外部スクリプトを壊さないため**フロントの配信ホスト（Nginx 等）側で**設定してください。JWT を localStorage に保持する設計上、本番では CSP の付与を強く推奨します。
- Prometheus メトリクスは `GET /metrics` で**未認証公開**されます（トラフィック量・レイテンシ・パス等が漏れます）。上記 Nginx 例では `location /api/` だけを backend へプロキシし `/metrics` は SPA フォールバックに落ちるため外部露出しませんが、全パスを backend へ転送する構成では `/metrics` を内部ネットワーク限定にするか Basic 認証等で保護してください。

## Webhook 受信

fincode からの定期課金結果 Webhook は FastAPI プロセスが同期で処理します。バックグラウンドワーカーは本スターターには含まれていません。Webhook ハンドラは署名検証 → 冪等性チェック → DB upsert を 1 リクエスト内で終わらせて 204 を返します。

メール通知や下流サービスのセットアップなど時間のかかる処理を入れる場合は、fork 側で別途キュー / ワーカーを追加してください。

## マイグレーションとロールバック

トラフィックを切り替える前に、Alembic migration を実行します。

```bash
uv run alembic upgrade head
```

ロールバック方針:

- データ変更を含むリリースは、巻き戻しではなく前進方向の修正（forward fix）を優先する。
- `uv run alembic downgrade <revision>` は、downgrade を検証済みの migration に限って使う。
- 適用済みの migration ファイルは編集しない。

## キーローテーション

fincode API キー:

1. fincode で新しい鍵ペアを発行する。
2. secret store を更新する。
3. 新しい環境変数でデプロイする。
4. 決済 API 呼び出しが成功することを確認する。
5. fincode 側で古いキーを無効化する。

## JWT トークン運用

API はログインで発行する JWT Bearer token を使います。スターターの既定は短命の access token のみです。JWT はサーバー側でトークンの状態を持たない限り、個別のトークンだけを無効化することはできません。fork では次のどれかを選び、ドキュメントに明記してください。

| 戦略 | トレードオフ |
| --- | --- |
| 短命の access token のみ | シンプル。ただし期限切れのたびに再ログインが必要 |
| access + refresh token | UX は良いが、refresh token の保存と失効管理が必要 |
| user 行に token version を持つ | アカウント侵害などのセキュリティ対応時に、全 token を一括で無効化できる |
| サーバー側 denylist | 単一の token だけを無効化できる。保存先と古いエントリの掃除が必要 |

モバイルアプリ、監視ジョブ、bot などの長期稼働クライアントは、リクエスト前のトークン期限切れ検知、`401 Unauthorized` のハンドリング、指数バックオフでのログイン再試行に対応してください。

### JWT secret のローテーション

`JWT_SECRET_KEY` を変えると、複数の検証キーをサポートしていない限り、既存の token はすべて無効になります。

推奨する本番手順:

1. key ID (`kid`) と複数の検証キーをサポートする実装を入れる。
2. 新しいキーで、新規 token への署名を開始する。
3. 古い token の期限が切れるまで、旧キーは検証用に残しておく。
4. 旧キーを削除する。

複数キーをサポートしない場合は、再ログインが必要になる時間帯をあらかじめ告知し、トラフィックが少ない時間帯に切り替えます。
