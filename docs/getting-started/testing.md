# テストガイド

テストは実際の fincode API に依存せず、アプリの挙動を検証します。バックエンドは `pytest`、フロントエンドは `Vitest`、API 契約は `Redocly CLI` で検証します。

## テストスタック

| レイヤ | ツール | 主な場所 |
| --- | --- | --- |
| Python / FastAPI | pytest, httpx AsyncClient | `backend/tests/` |
| データベース | testcontainers-python（PostgreSQL 16）+ Alembic | `backend/tests/conftest.py` |
| React | Vitest | `frontend/src/**/*.test.ts(x)` |
| API契約 | Redocly CLI | `docs/api/openapi.yml` |

## コマンド

```bash
# バックエンド
cd backend
uv run pytest                                # 全テスト
uv run pytest tests/test_auth.py             # 単一ファイル
uv run pytest --cov=app --cov-report=term-missing

# フロントエンド
cd frontend
npm run test:run

# OpenAPI 仕様
npx @redocly/cli lint docs/api/openapi.yml
```

## DB テスト

PostgreSQL 固有機能（JSONB、partial unique index）を使うため、SQLite では代替できません。`backend/tests/conftest.py` が次のことを自動で行います。

- セッション開始時に `testcontainers-python` で PostgreSQL 16 コンテナを起動
- Alembic の `upgrade head` でスキーマを構築
- 各テストの前に全テーブルを TRUNCATE し、slowapi のレート制限カウンタもリセット

そのため `TEST_DATABASE_URL` のような環境変数や、テスト用 DB の手動準備は不要です。Docker Desktop が起動している必要があります。

## 認証付きリクエスト

`auth_client` フィクスチャを使うと、登録済みユーザーで認証ヘッダー付きの `httpx.AsyncClient` が手に入ります。新規登録は `registered_user` フィクスチャが `POST /api/register` を呼びます。

## fincode をモックする

自動テストから fincode のテスト環境 API を呼び出してはいけません。レイテンシ、レート制限、秘密情報の管理、結果が安定しないリスクなどが増えるためです。

モック境界の選び方:

- 低レベル HTTP テスト: `httpx.MockTransport` で `FincodeHttpClient` を直接駆動
- ドメインサービス / API ルートのテスト: `app.dependency_overrides[get_fincode_client]` で `FincodeClient` プロトコルを満たす fake 実装に差し替える

fake クライアントの実装例:

```python
class FakeFincodeClient:
    async def create_customer(self, *, idempotency_key: str) -> dict:
        return {"id": "cust_test", "raw": {}}

    async def get_plan(self, plan_id: str) -> dict:
        return {
            "id": plan_id,
            "plan_name": "Standard",
            "amount": "1000",
            "interval": "month",
        }
```

## API テスト

API テストは `httpx.AsyncClient` 経由で FastAPI ルートを駆動し、次を確認します。

- HTTP ステータスコード
- レスポンス schema（`detail.code` / `detail.message` の形）
- DB 状態（カード行、契約行、`audit_logs` の挿入など）
- カード番号や CVC を受け付けず、保存もしないこと

## レース系テスト

「1 ユーザー = 最大 1 アクティブ契約」のような不変条件は、`asyncio.gather` で複数タスクを同時に起動して検証します。PostgreSQL の partial unique index が `IntegrityError` を返すこと、それがアプリの例外（`ActiveSubscriptionExistsError`）に変換されることを確認します。

## 優先するシナリオ

カバレッジの数値はあくまで補助的な指標です。次のシナリオは必ずカバーしてください。

- 登録 / ログインと JWT 保護エンドポイント
- カードトークン登録の成功と fincode 失敗
- アクティブ契約の一意性（race を含む）
- 解約フロー
- Webhook の署名検証と冪等性
- fincode timeout / rate-limit / server-error の HTTP マッピング
