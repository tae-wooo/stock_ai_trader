import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import get_db
from app.database.models import CandidateStock


ALLOWED_STATUSES = {
    "CANDIDATE",
    "AUTO_REGISTERED",
    "AI_ANALYZED",
    "RISK_BLOCKED",
    "PRICE_FILTERED",
}


def main():
    if len(sys.argv) != 3:
        print("사용법:")
        print("python scripts/update_candidate_status.py 종목코드 상태")
        print()
        print("예시:")
        print("python scripts/update_candidate_status.py 005930 AUTO_REGISTERED")
        print()
        print("가능한 상태:")
        for status in sorted(ALLOWED_STATUSES):
            print(f"- {status}")
        return

    stock_code = sys.argv[1].strip()
    new_status = sys.argv[2].strip().upper()

    if new_status not in ALLOWED_STATUSES:
        print(f"잘못된 상태입니다: {new_status}")
        print("가능한 상태:")
        for status in sorted(ALLOWED_STATUSES):
            print(f"- {status}")
        return

    db = get_db()

    candidate = (
        db.query(CandidateStock)
        .filter(CandidateStock.stock_code == stock_code)
        .first()
    )

    if not candidate:
        print(f"후보 종목을 찾지 못했습니다: {stock_code}")
        return

    old_status = candidate.status
    candidate.status = new_status

    db.commit()

    print("후보 상태 변경 완료")
    print("=" * 70)
    print(f"종목: {candidate.stock_name}({candidate.stock_code})")
    print(f"기존 상태: {old_status}")
    print(f"변경 상태: {new_status}")


if __name__ == "__main__":
    main()
