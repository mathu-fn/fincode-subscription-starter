from fastapi import APIRouter

from app.api.routes import auth, cards, subscriptions, webhooks

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(cards.router)
api_router.include_router(subscriptions.router)
api_router.include_router(webhooks.router)
