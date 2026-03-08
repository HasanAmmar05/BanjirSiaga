import httpx
import json
from app.core.config import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

async def call_groq_fallback(system_instruction: str, user_prompt: str) -> dict:
    """Fallback to Groq Llama 3 when Gemini fails due to rate limits.
    Uses LLaMA 3.3 70B via the Groq API using HTTPX to avoid new dependencies."""
    
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set.")
    
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(GROQ_API_URL, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        data = response.json()
        
        # Groq returns standard OpenAI-compatible messages
        content = data["choices"][0]["message"]["content"]
        
        # content is guaranteed to be a JSON string due to json_object response format
        return json.loads(content)
