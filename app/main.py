from fastapi import FastAPI
from app.api.router import api_router

app = FastAPI(
    title="Commodore Webhook API",
    description="Multi-platform webhook service for WhatsApp Cloud API and Google Chat using Gemini AI.",
    version="1.0.0"
)

app.include_router(api_router)
