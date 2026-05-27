# Fincode Webhook 統合

定期課金の結果は fincode から非同期で届きます。Webhook を使って、ローカルの `subscription_results` と契約ステータスを実際の課金結果に合わせます。

## エンドポイント

推奨ルート:

```text
POST /api/webhooks/fincode
```

FastAPIでの形:

```python
@router.post("/webhooks/fincode", status_code=204)
async def fincode_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    handler: FincodeWebhookHandler = Depends(get_fincode_webhook_handler),
) -> None:
    payload = await request.body()
    signature = request.headers.get("Fincode-Signature")
    await handler.handle(payload=payload, signature=signature, db=db)
```

このルートはユーザーからではなく fincode から呼ばれるため、JWT では保護しません。必ず署名検証で保護します。

## 署名検証

署名は、payload を parse したり DB を変更したりする前に検証します。正確なヘッダー名とアルゴリズムは fincode の公式ドキュメントで確認してください。

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
```

secret は `FINCODE_WEBHOOK_SECRET` として保存します。ローテーションは fincode 側を先に変え、その後に自分の環境変数を変えます。

## 冪等性

Webhook は at-least-once（少なくとも 1 回は届く）方式です。同じイベントが複数回届く可能性があります。

次のどちらか、または両方を使います。

- fincode event ID を `webhook_events_seen` に保存する。
- `(fincode_subscription_id, fincode_payment_id)` をキーに `subscription_results` を upsert する。

2回目以降の配送では、すでに保存済みであることを確認して成功を返します。

## 処理方針

Webhook ハンドラーは、課金イベントを受け取る独立した処理として扱います。

1. 署名を検証する。
2. payload を parse して検証する。
3. fincode subscription ID からローカル契約を探す。
4. `subscription_results` を upsert する。
5. 必要に応じて契約ステータスを更新する。
6. 監査ポリシーに合わせて、`user_id = NULL` または契約の持ち主ユーザーで監査ログを書く。
7. 通知や下流サービスのセットアップ用に、ドメインイベントを発行する。

Webhook handler から同期的な契約登録フローを呼び出さないでください。

## レスポンス

| レスポンス | 意味 |
| --- | --- |
| `204 No Content` | イベントを保存済み。fincode は再送を止めてよい |
| `400/401/422` | 署名不正や payload 不正など、再送しても解決しない失敗 |
| `5xx` | 一時的な失敗。fincode が再送する可能性あり |

未知のイベントでも形式が正しいものは、再送しても解決しない場合は dead-letter テーブルに保存して ack（受信成功）を返します。

## ローカルテスト

実際の fincode からの配信を試す場合は、ngrok などのトンネルを使います。

```bash
ngrok http 8000
```

または、既知の署名付き fixture を POST します。

```bash
curl -X POST http://localhost:8000/api/webhooks/fincode \
  -H "Fincode-Signature: $signature" \
  -H "Content-Type: application/json" \
  -d "$payload"
```
