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

JWT secret は、ユーザーに再ログインしてもらう期間をあらかじめ告知して切り替えるか、key ID と複数の検証キーをサポートする実装を入れてからローテーションします。
