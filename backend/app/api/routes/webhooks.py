from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, status

from app.api.deps import AuditLoggerDep, SessionDep, SettingsDep
from app.core.rate_limit import limiter
from app.services.fincode.webhook_handler import FincodeWebhookHandler

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/fincode", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
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
