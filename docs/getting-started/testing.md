# テストガイド

テストは実際の fincode API に依存せず、アプリの挙動を検証します。

## テストスタック

| レイヤ | ツール | 主な場所 |
| --- | --- | --- |
| Python / FastAPI | pytest, httpx TestClient | `tests/` |
| データベース | SQLAlchemy test session + Alembic | `tests/integration/` |
| React | Vitest | `frontend/src/**/*.test.ts(x)` |
| API契約 | Redocly CLI | `docs/api/openapi.yml` |

## コマンド

```bash
uv run pytest
uv run pytest tests/unit
uv run pytest tests/integration
npm run test
npx @redocly/cli lint docs/api/openapi.yml
```

テストでは `TEST_DATABASE_URL` を使い、開発DBとは分けてください。

## DBテスト

Integration test はテストセッション開始時にクリーンなスキーマを作るか、`TEST_DATABASE_URL` に対して Alembic migration を実行します。

推奨方針:

- PostgreSQL 固有機能（JSONB、partial unique index）を使うため SQLite で代替しない。テストは `testcontainers-python` で一時 PostgreSQL を立ち上げる。
- テスト間はトランザクションrollbackまたはtruncateで状態を消す。
- 共有seedではなくfactoryを使う。
- 契約・カード操作後のDB状態をassertする。

## fincodeをモックする

自動テストから fincode テストモードを呼ばないでください。レイテンシ、レート制限、非決定性、秘密情報管理のリスクが増えます。

モック境界の例:

- `FincodeClient` の低レベルテストでは `httpx.MockTransport`。
- `CustomerService`、`CardService`、`PlanService`、`SubscriptionService` はservice fake。
- `/api/webhooks/fincode` はpayload fixture。

service fake の例:

```python
class FakePlanService:
    async def fetch_plan(self, plan_id: str):
        return {
            "id": plan_id,
            "name": "Standard",
            "amount": 1000,
            "interval": "month",
            "raw": {"id": plan_id},
        }
```

## APIテスト

APIテストは `TestClient` または `httpx.AsyncClient` で FastAPI route を駆動し、次を確認します。

- ステータスコード。
- レスポンスschema。
- DB状態。
- 成功した状態変更で監査ログが作られること。
- カード番号のフル値を受け付けず、保存もしないこと。

## カバレッジ

カバレッジは品質の補助指標であり、シナリオ網羅の代わりではありません。

```bash
uv run pytest --cov=app --cov-report=term-missing
```

優先度の高いシナリオ:

- 登録/ログインとJWT保護エンドポイント。
- カードトークン登録成功とfincode失敗。
- アクティブ契約の一意性。
- 解約。
- Webhook冪等性。
- fincode timeout/rate-limit/server-error のHTTPマッピング。
