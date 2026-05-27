from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_audit_logger_dep,
    get_current_user,
    get_fincode_client,
    get_session,
)
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.card import CardOut, CreateCardRequest
from app.services.audit_logger import AuditLogger
from app.services.card_manager import CardManager
from app.services.fincode.client import FincodeClient

router = APIRouter(prefix="/api/subscription/cards", tags=["cards"])


@router.get("", response_model=list[CardOut])
@limiter.limit("60/minute")
async def list_cards(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    client: FincodeClient = Depends(get_fincode_client),
) -> list[CardOut]:
    manager = CardManager(client)
    cards = await manager.list_cards(db, user)
    return [CardOut.model_validate(c) for c in cards]


@router.post("", response_model=CardOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_card(
    request: Request,
    payload: CreateCardRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    client: FincodeClient = Depends(get_fincode_client),
    audit: AuditLogger = Depends(get_audit_logger_dep),
) -> CardOut:
    manager = CardManager(client, audit=audit)
    card = await manager.register_card(db, user, payload.token)
    await db.commit()
    await db.refresh(card)
    return CardOut.model_validate(card)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def delete_card(
    request: Request,
    card_id: int,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
    client: FincodeClient = Depends(get_fincode_client),
    audit: AuditLogger = Depends(get_audit_logger_dep),
) -> None:
    manager = CardManager(client, audit=audit)
    await manager.delete_card(db, user, card_id)
    await db.commit()
