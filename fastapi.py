from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import os
from datetime import datetime, timezone
import json
import httpx
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY environment variable is not set."
        )
    return genai.Client(api_key=api_key)


async def send_whatsapp_message(to_number: str, text: str):
    """Sends a text message back to the user via Meta WhatsApp Cloud API."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID or WHATSAPP_TOKEN.startswith("your_"):
        print("[WARNING] WHATSAPP_TOKEN or PHONE_NUMBER_ID is not configured in .env!")
        return

    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response_json = response.json()
            if response.status_code == 200:
                print(f"[WhatsApp] Message sent successfully to {to_number}")
            else:
                print(f"[WhatsApp Error] Failed to send message ({response.status_code}): {response_json}")
        except Exception as e:
            print(f"[WhatsApp Exception] Error sending message: {e}")


@app.get("/", response_class=PlainTextResponse)
@app.get("/whatsapp-webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """Webhook verification endpoint required by Meta WhatsApp Cloud API."""
    params = request.query_params

    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge")
    token = params.get("hub.verify_token")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("[WhatsApp] WEBHOOK VERIFIED SUCCESSFULLY")
        return challenge

    print(f"[WhatsApp Verification Failed] Invalid token or mode. Provided token: {token}")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/")
@app.post("/whatsapp-webhook")
async def receive_webhook(request: Request):
    """Receives incoming WhatsApp webhook notifications from Meta."""
    body = await request.json()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[Webhook Received {timestamp}]")

    # Check if payload is from Meta WhatsApp Cloud API
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

                            # Process prompt with Gemini
                            try:
                                client = get_gemini_client()
                                response = client.models.generate_content(
                                    model="gemini-3.1-flash-preview",
                                    contents=user_text
                                )
                                response_text = response.text
                            except Exception as e:
                                print(f"Error calling Gemini API: {e}")
                                response_text = f"Disculpa, ocurrió un error procesando tu solicitud: {str(e)}"

                            # Send reply via WhatsApp
                            await send_whatsapp_message(sender_id, response_text)

    return {"status": "ok"}


@app.post("/chat-webhook")
async def chat_webhook(request: Request):
    """Endpoint kept for Google Chat compatibility."""
    body = await request.json()

    print("\n[Google Chat Webhook Event Received]")
    print(json.dumps(body, indent=2))

    is_addon_format = "chat" in body and "commonEventObject" in body
    user_message_text = ""
    event_type = body.get("type")

    if is_addon_format:
        message_payload = body.get("chat", {}).get("messagePayload", {})
        message = message_payload.get("message", {})
        user_message_text = message.get("text", "")
        if not user_message_text:
            user_message_text = message.get("argumentText", "")
    else:
        if event_type == "ADDED_TO_SPACE":
            return {"text": "Hello! I am a Gemini-powered bot. Ask me anything!"}
        elif event_type == "MESSAGE":
            message = body.get("message", {})
            user_message_text = message.get("text", "")

    if user_message_text:
        try:
            client = get_gemini_client()
            response = client.models.generate_content(
                model="gemini-3.1-flash-preview",
                contents=user_message_text
            )
            response_text = response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            response_text = f"Error processing request: {str(e)}"
    else:
        response_text = "I received an event but couldn't find a message to respond to."

    if is_addon_format:
        return {
            "hostAppDataAction": {
                "chatDataAction": {
                    "createMessageAction": {
                        "message": {"text": response_text}
                    }
                }
            }
        }
    else:
        return {"text": response_text}


