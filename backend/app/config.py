"""
Application Configuration — Bachmann's Rule: Never hardcode. Always configure.

Uses pydantic-settings for type-safe environment variable loading.
Falls back to sensible defaults for local development.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    Central configuration loaded from .env file or environment variables.
    Every setting has a sensible default for local dev.
    """

    # App
    APP_NAME: str = "Wakeel AI"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Database — SQLite for dev, PostgreSQL for production
    DATABASE_URL: str = "sqlite:///./wakeel.db"

    # JWT Authentication
    JWT_SECRET_KEY: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # OpenAI (legacy fallback)
    OPENAI_API_KEY: str = ""

    # Anthropic (primary LLM — Claude)
    ANTHROPIC_API_KEY: str = ""

    # Google Cloud (primary transcription — Speech-to-Text)
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_CLOUD_LOCATION: str = "global"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # Groq (free Whisper transcription — whisper-large-v3)
    GROQ_API_KEY: str = ""

    # Twilio (WhatsApp Business)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""

    @property
    def has_twilio(self) -> bool:
        return bool(
            self.TWILIO_ACCOUNT_SID
            and self.TWILIO_AUTH_TOKEN
            and self.TWILIO_ACCOUNT_SID != "your-twilio-sid"
        )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def has_groq_key(self) -> bool:
        return bool(self.GROQ_API_KEY and self.GROQ_API_KEY != "your-groq-key")

    @property
    def has_openai_key(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY != "sk-your-openai-key")

    @property
    def has_anthropic_key(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY and self.ANTHROPIC_API_KEY != "your-anthropic-key")

    @property
    def has_google_cloud(self) -> bool:
        return bool(self.GOOGLE_CLOUD_PROJECT_ID and self.GOOGLE_CLOUD_PROJECT_ID != "your-project-id")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
