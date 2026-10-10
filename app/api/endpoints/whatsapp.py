from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse
from datetime import datetime, timezone

from app import config
from app.services.gemini import generate_gemini_response
from app.services.whatsapp import send_whatsapp_message

router = APIRouter(tags=["WhatsApp"])

@router.get("/", response_class=PlainTextResponse)
@router.get("/whatsapp-webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """Webhook verification endpoint required by Meta WhatsApp Cloud API."""
    params = request.query_params

    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge")
    token = params.get("hub.verify_token")

    if mode == "subscribe" and token == config.VERIFY_TOKEN:
        print("[WhatsApp] WEBHOOK VERIFIED SUCCESSFULLY")
        return challenge

    print(f"[WhatsApp Verification Failed] Invalid token or mode. Provided token: {token}")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/")
@router.post("/whatsapp-webhook")
async def receive_webhook(request: Request):
    """Receives incoming WhatsApp webhook notifications from Meta."""
    body = await request.json()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[Webhook Received {timestamp}]")

    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                if messages:
                    for msg in messages:
                        sender_id = msg.get("from")
                        msg_type = msg.get("type")

                        if msg_type == "text":
                            user_text = msg.get("text", {}).get("body", "")
                            print(f"\n[WhatsApp Message from {sender_id}]: {user_text}")

                            try:
                                response_text = generate_gemini_response(user_text)
                            except Exception as e:
                                print(f"Error calling Gemini API: {e}")
                                response_text = f"Disculpa, ocurrió un error procesando tu solicitud: {str(e)}"

                            await send_whatsapp_message(sender_id, response_text)

    return {"status": "ok"}
