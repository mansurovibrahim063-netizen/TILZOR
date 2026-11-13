import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    ADMIN_TELEGRAM_ID: int = 0

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    WEB_HOST: str = "127.0.0.1"
    WEB_PORT: int = 8000
    ADMIN_PASSWORD: str = "admin123"
    SECRET_KEY: str = "super-secret-key-change-me"

    DATABASE_URL: str = "sqlite+aiosqlite:///./moderator.db"

    AUTO_TRANSLATE: bool = True
    STRICT_LINK_BLOCKING: bool = True
    TOXICITY_THRESHOLD: int = 65
    ENABLE_FLOOD_PROTECTION: bool = True
    FLOOD_WINDOW_SECONDS: int = 60
    FLOOD_MAX_IDENTICAL_MESSAGES: int = 2

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
