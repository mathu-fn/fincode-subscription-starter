from fastapi import APIRouter, Request, status

from app.api.deps import (
    CardManagerDep,
    CurrentUserDep,
    SessionDep,
)
from app.core.rate_limit import limiter
from app.schemas.card import CardOut, CreateCardRequest

router = APIRouter(prefix="/subscription/cards", tags=["cards"])


@router.get("", response_model=list[CardOut])
@limiter.limit("60/minute")
async def list_cards(
    request: Request,
    db: SessionDep,
    user: CurrentUserDep,
    manager: CardManagerDep,
) -> list[CardOut]:
    cards = await manager.list_cards(db, user)
    return [CardOut.model_validate(c) for c in cards]


@router.post("", response_model=CardOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_card(
    request: Request,
    payload: CreateCardRequest,
    db: SessionDep,
    user: CurrentUserDep,
    manager: CardManagerDep,
) -> CardOut:
    card = await manager.register_card(db, user, payload.token)
    await db.commit()
    await db.refresh(card)
    return CardOut.model_validate(card)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def delete_card(
    request: Request,
    card_id: int,
    db: SessionDep,
    user: CurrentUserDep,
    manager: CardManagerDep,
) -> None:
    await manager.delete_card(db, user, card_id)
    await db.commit()
