# 本番デプロイ

Nginx、Uvicorn、PostgreSQL 16+、systemd などのプロセスマネージャを使ったセルフホストLinux環境の参考手順です。

## チェックリスト

| 項目 | 必須 | 補足 |
| --- | --- | --- |
| `APP_ENV=production` | 必須 | 開発用挙動を無効化 |
| `APP_URL` / `API_URL` | 必須 | 公開originと一致させる |
| `DATABASE_URL` | 必須 | 本番DB認証情報はsecret storeから渡す |
| `JWT_SECRET_KEY` | 必須 | 強いランダム値。計画的にローテーション |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 必須 | リスクモデルに合わせて短く設定 |
| `FINCODE_API_KEY=m_prod_...` | 必須 | 本番secret key |
| `FINCODE_PUBLIC_KEY=p_prod_...` | 必須 | ブラウザでのトークン化用公開鍵 |
| `FINCODE_BASE_URL=https://api.fincode.jp` | 必須 | 本番fincode endpoint |
| `FINCODE_WEBHOOK_SECRET` | 必須 | Webhookを使う場合 |
| HTTPS | 必須 | 認証と決済UXに必須 |
| 構造化ログ | 推奨 | CloudWatch、Datadog、Lokiなどへ集約 |

## ビルド

```bash
git fetch --all
git checkout <release-tag-or-sha>

uv sync --frozen --no-dev
npm ci
npm run build

uv run alembic upgrade head
```

フロントエンドのビルド成果物は Nginx、CDN、同一ホストなど、デプロイ形態に応じて配信します。

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

トラフィックが増える場合は Gunicorn 経由で Uvicorn worker を起動します。

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

## バックグラウンドワーカー

Celery、RQ、Dramatiqなどを使うforkでは、APIとは別サービスとしてworkerを常駐させ、APIと同じコードバージョンでデプロイします。Webhookや照合ジョブは冪等にしてください。

## マイグレーションとロールバック

トラフィック切替前に Alembic migration を実行します。

```bash
uv run alembic upgrade head
```

ロールバック方針:

- データ変更を含むリリースは forward fix を優先。
- `uv run alembic downgrade <revision>` は downgrade 検証済みmigrationに限定。
- 適用済みmigrationファイルは編集しない。

## キーローテーション

fincode APIキー:

1. fincodeで新しいkey pairを発行。
2. secret storeを更新。
3. 新しい環境変数でデプロイ。
4. 決済API呼び出し成功を確認。
5. fincodeで古いキーを失効。

JWT secret は計画的な再ログイン期間を設けるか、key ID と複数検証キーを実装してからローテーションします。
