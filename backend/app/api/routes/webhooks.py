from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_logger_dep, get_session
from app.core.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.services.audit_logger import AuditLogger
from app.services.fincode.webhook_handler import FincodeWebhookHandler

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/fincode", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
async def fincode_webhook(
    request: Request,
    fincode_signature: str | None = Header(default=None, alias="Fincode-Signature"),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    audit: AuditLogger = Depends(get_audit_logger_dep),
) -> Response:
    body = await request.body()
    handler = FincodeWebhookHandler(secret=settings.fincode_webhook_secret, audit=audit)
    await handler.handle(payload=body, signature=fincode_signature, db=db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
