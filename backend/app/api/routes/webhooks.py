from typing import Annotated

from fastapi import APIRouter, Header, Request, Response, status

from app.api.deps import AuditLoggerDep, SessionDep, SettingsDep
from app.core.exceptions import PayloadTooLargeError
from app.services.fincode.webhook_handler import FincodeWebhookHandler

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# fincode の Webhook ペイロードは小さな JSON。この上限は正当な配信には十分広く、
# 未認証・レート制限なしのこのエンドポイントに巨大ボディを流し込むメモリ枯渇 DoS を防ぐ。
_MAX_WEBHOOK_BODY_BYTES = 64 * 1024


async def _read_limited_body(request: Request, max_bytes: int) -> bytes:
    # まず Content-Length で弾き、本文を読む前に確保を避ける。
    content_length = request.headers.get("content-length")
    if content_length is not None and content_length.isdigit() and int(content_length) > max_bytes:
        raise PayloadTooLargeError()
    # Content-Length の欠落（chunked）や過少申告に備え、実ストリームも上限で打ち切る。
    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > max_bytes:
            raise PayloadTooLargeError()
        chunks.append(chunk)
    return b"".join(chunks)


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
    body = await _read_limited_body(request, _MAX_WEBHOOK_BODY_BYTES)
    handler = FincodeWebhookHandler(secret=settings.fincode_webhook_secret, audit=audit)
    await handler.handle(payload=body, signature=fincode_signature, db=db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
