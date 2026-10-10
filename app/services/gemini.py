from google import genai
from fastapi import HTTPException
from app import config

def get_gemini_client():
    if not config.GEMINI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY environment variable is not set."
        )
    return genai.Client(api_key=config.GEMINI_API_KEY)

def generate_gemini_response(prompt: str, model: str = "gemini-3.6-flash") -> str:
    """Generates content using Gemini API."""
    client = get_gemini_client()
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text
