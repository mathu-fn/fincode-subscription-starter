from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, status

from app.api.deps import AuditLoggerDep, SessionDep, SettingsDep
from app.services.fincode.webhook_handler import FincodeWebhookHandler

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# レートリミットは意図的に付けない。fincode は少数の固定 IP から送信するため
# IP キーのリミットは全 Webhook が単一バケットを共有し、正当な再送バーストを
# 429 で弾いて再配信の失敗を招く。不正リクエストは HMAC 署名検証で 401 になり、
# 重複は二段冪等（webhook_events_seen + upsert）が吸収する。
@router.post("/fincode", status_code=status.HTTP_204_NO_CONTENT)
async def fincode_webhook(
    request: Request,
    db: SessionDep,
    settings: SettingsDep,
    audit: AuditLoggerDep,
    fincode_signature: Annotated[str | None, Header(alias="Fincode-Signature")] = None,
) -> Response:
    body = await request.body()
    handler = FincodeWebhookHandler(secret=settings.fincode_webhook_secret, audit=audit)
    await handler.handle(payload=body, signature=fincode_signature, db=db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
