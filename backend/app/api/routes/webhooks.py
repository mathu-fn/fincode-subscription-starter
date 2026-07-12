from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, status

from app.api.deps import SessionDep, WebhookHandlerDep

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# レートリミットは意図的に付けない。fincode は少数の固定 IP から送信するため
# IP キーのリミットは全 Webhook が単一バケットを共有し、正当な再送バーストを
# 429 で弾いて再配信の失敗を招く。不正リクエストは HMAC 署名検証で 401 になり、
# 重複は二段冪等（webhook_events_seen + upsert）が吸収する。
@router.post("/fincode", status_code=status.HTTP_204_NO_CONTENT)
async def fincode_webhook(
    request: Request,
    db: SessionDep,
    handler: WebhookHandlerDep,
    fincode_signature: Annotated[str | None, Header(alias="Fincode-Signature")] = None,
) -> Response:
    body = await request.body()
    await handler.handle(payload=body, signature=fincode_signature, db=db)
    # トランザクションの所有はルーター側（他の Manager フローと同じ規約）。
    # ハンドラーが例外を出した場合はコミットに到達せず、get_session のセッション
    # クローズ時に未コミットの変更がロールバックされる。
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
