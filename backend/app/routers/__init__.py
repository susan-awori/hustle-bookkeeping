from fastapi import APIRouter

from app.routers import auth, ledger, voice

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(voice.router)
api_router.include_router(ledger.router)
