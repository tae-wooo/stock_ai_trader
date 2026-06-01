import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BASE_DIR / ".env")


class Settings:
    NAVER_CLIENT_ID: str | None = os.getenv("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET: str | None = os.getenv("NAVER_CLIENT_SECRET")

    DART_API_KEY: str | None = os.getenv("DART_API_KEY")

    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    DISCORD_WEBHOOK_URL: str | None = os.getenv("DISCORD_WEBHOOK_URL")

    KRX_ID: str | None = os.getenv("KRX_ID")
    KRX_PW: str | None = os.getenv("KRX_PW")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///data/stock_ai_trader.db",
    )

    TZ: str = os.getenv("TZ", "Asia/Seoul")


settings = Settings()
