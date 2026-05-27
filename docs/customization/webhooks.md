# Fincode Webhook 統合

定期課金結果は fincode から非同期で届きます。Webhookにより、ローカルの `subscription_results` と契約ステータスを実際の課金結果に合わせます。

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

このルートはユーザーからではなく fincode から呼ばれるため、JWTでは保護しません。必ず署名検証で保護します。

## 署名検証

署名は、payloadをparseしたりDBを変更したりする前に検証します。正確なヘッダー名とアルゴリズムは fincode の公式ドキュメントで確認してください。

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
```

secret は `FINCODE_WEBHOOK_SECRET` として保存します。ローテーションは fincode 側を先に変え、その後に自分の環境変数を変えます。

## 冪等性

Webhookは at-least-once です。同じイベントが複数回届く可能性があります。

次のどちらか、または両方を使います。

- fincode event ID を `webhook_events_seen` に保存する。
- `(fincode_subscription_id, fincode_payment_id)` をキーに `subscription_results` を upsert する。

2回目以降の配送では、既に永続化済みであることを確認して成功を返します。

## 処理方針

Webhook handler は課金イベントの独立したconsumerとして扱います。

1. 署名を検証する。
2. payloadをparseして検証する。
3. fincode subscription ID からローカル契約を探す。
4. `subscription_results` を upsert する。
5. 必要に応じて契約ステータスを更新する。
6. 監査ポリシーに応じて `user_id = NULL` または所有ユーザーで監査ログを書く。
7. 通知やプロビジョニング用のdomain eventを発行する。

Webhook handler から同期的な契約登録フローを呼び出さないでください。

## レスポンス

| レスポンス | 意味 |
| --- | --- |
| `204 No Content` | イベントを永続化済み。fincodeは再送を止めてよい |
| `400/401/422` | 署名不正やpayload不正などの永続的失敗 |
| `5xx` | 一時的失敗。fincodeが再送する可能性あり |

未知だが形式として正しいイベントは、再送で解決しないならdead-letter tableへ保存してackします。

## ローカルテスト

実際のfincode配送を試す場合は ngrok などのトンネルを使います。

```bash
ngrok http 8000
```

または既知の署名付きfixtureをPOSTします。

```bash
curl -X POST http://localhost:8000/api/webhooks/fincode \
  -H "Fincode-Signature: $signature" \
  -H "Content-Type: application/json" \
  -d "$payload"
```
