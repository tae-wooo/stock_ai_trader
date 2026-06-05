import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH)


class Settings:
    """
    프로젝트 전체 환경설정.

    원칙:
    - 실제 API 키와 Webhook URL은 .env에만 둔다.
    - GitHub에는 .env.example만 올린다.
    - Docker 실행 시 docker-compose.yml의 environment 값이 .env보다 우선될 수 있다.
    """

    BASE_DIR: Path = BASE_DIR
    ENV_PATH: Path = ENV_PATH

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

    def validate_required(self, keys: Iterable[str]) -> None:
        """
        실행 전에 필요한 환경변수가 있는지 검증한다.

        예:
            settings.validate_required([
                "NAVER_CLIENT_ID",
                "NAVER_CLIENT_SECRET",
            ])
        """
        missing: list[str] = []

        for key in keys:
            value = getattr(self, key, None)
            if value is None or str(value).strip() == "":
                missing.append(key)

        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(
                f"필수 환경변수가 없습니다: {joined}\n"
                f".env 파일을 확인하세요: {self.ENV_PATH}"
            )

    def has_naver(self) -> bool:
        return bool(
            self.NAVER_CLIENT_ID
            and self.NAVER_CLIENT_ID.strip()
            and self.NAVER_CLIENT_SECRET
            and self.NAVER_CLIENT_SECRET.strip()
        )

    def has_dart(self) -> bool:
        return bool(self.DART_API_KEY and self.DART_API_KEY.strip())

    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip())

    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip())

    def has_discord(self) -> bool:
        return bool(
            self.DISCORD_WEBHOOK_URL
            and self.DISCORD_WEBHOOK_URL.strip()
        )


settings = Settings()
