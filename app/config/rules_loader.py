import json
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parent


def load_json_config(filename: str) -> dict:
    path = CONFIG_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_theme_keywords() -> dict:
    return load_json_config("theme_keywords.json")


def load_trade_rules() -> dict:
    return load_json_config("trade_rules.json")
