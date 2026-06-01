import os
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()


class DiscordService:
    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

        if not self.webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL이 .env에 설정되어 있지 않습니다.")

    def send_message(self, content: str):
        payload = {
            "content": content,
        }

        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=20,
        )

        response.raise_for_status()

    def send_file_with_message(self, content: str, file_path: Path):
        if not file_path.exists():
            raise FileNotFoundError(f"전송할 파일을 찾을 수 없습니다: {file_path}")

        payload = {
            "content": content,
        }

        with open(file_path, "rb") as f:
            files = {
                "file": (
                    file_path.name,
                    f,
                    "text/plain",
                )
            }

            response = requests.post(
                self.webhook_url,
                data={"payload_json": __import__("json").dumps(payload, ensure_ascii=False)},
                files=files,
                timeout=30,
            )

        response.raise_for_status()
