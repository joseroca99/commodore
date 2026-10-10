import httpx
from app import config

async def send_whatsapp_message(to_number: str, text: str):
    """Sends a text message back to the user via Meta WhatsApp Cloud API."""
    if not config.WHATSAPP_TOKEN or not config.PHONE_NUMBER_ID or config.WHATSAPP_TOKEN.startswith("your_"):
        print("[WARNING] WHATSAPP_TOKEN or PHONE_NUMBER_ID is not configured in .env!")
        return

    url = f"https://graph.facebook.com/v21.0/{config.PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
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
