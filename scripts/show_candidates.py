import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import get_db
from app.database.models import CandidateStock


def from_json_text(value: str | None):
    if not value:
        return []

    try:
        return json.loads(value)
    except Exception:
        return []


def main():
    db = get_db()

    candidates = (
        db.query(CandidateStock)
        .order_by(
            CandidateStock.score.desc(),
            CandidateStock.last_detected_at.desc(),
        )
        .limit(50)
        .all()
    )

    if not candidates:
        print("저장된 후보 종목이 없습니다.")
        return

    print("후보 종목 상태 목록")
    print("=" * 100)

    for idx, item in enumerate(candidates, start=1):
        detected_keywords = from_json_text(item.detected_keywords)
        positive_keywords = from_json_text(item.positive_keywords)
        negative_keywords = from_json_text(item.negative_keywords)

        print(
            f"[{idx}] {item.stock_name}({item.stock_code}) "
            f"/ score={item.score} "
            f"/ status={item.status} "
            f"/ news={item.news_count} "
            f"/ themes={item.theme_keyword_count} "
            f"/ positive={item.positive_keyword_count} "
            f"/ risk={item.negative_keyword_count}"
        )

        print(f"    테마: {', '.join(detected_keywords) if detected_keywords else '-'}")
        print(f"    긍정: {', '.join(positive_keywords) if positive_keywords else '-'}")
        print(f"    위험: {', '.join(negative_keywords) if negative_keywords else '-'}")
        print(f"    최근 감지: {item.last_detected_at}")
        print("-" * 100)


if __name__ == "__main__":
    main()
