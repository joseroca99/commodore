from fastapi import APIRouter
from app.api.endpoints import whatsapp, google_chat

api_router = APIRouter()
api_router.include_router(whatsapp.router)
api_router.include_router(google_chat.router)
