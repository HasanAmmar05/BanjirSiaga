import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "BanjirSiaga"
    GEMINI_API_KEY: str
    GROQ_API_KEY: str | None = None
    SUPABASE_URL: str
    SUPABASE_KEY: str

    class Config:
        env_file = ".env.local"
        extra = 'ignore'

settings = Settings()
