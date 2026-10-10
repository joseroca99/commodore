import json
from fastapi import APIRouter, Request
from app.services.gemini import generate_gemini_response

router = APIRouter(tags=["Google Chat"])

@router.post("/chat-webhook")
async def chat_webhook(request: Request):
    """Endpoint for Google Chat webhook compatibility."""
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
            response_text = generate_gemini_response(user_message_text)
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
