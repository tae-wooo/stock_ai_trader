import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.analysis.disclosure_scoring import score_disclosures
from app.database.connection import get_db
from app.database.models import Disclosure
from app.services.stock_service import StockService


def main():
    db = get_db()
    stock_service = StockService(db)

    stocks = stock_service.get_all_stocks()

    if not stocks:
        print("등록된 관심종목이 없습니다.")
        print("먼저 python scripts/add_stock.py 로 종목을 등록하세요.")
        return

    print("등록된 관심종목")
    print("-" * 40)

    for stock in stocks:
        print(f"{stock.id}. {stock.name}({stock.code})")

    print("-" * 40)

    stock_code = input("공시 점수를 계산할 종목코드 입력: ").strip()

    target_stock = None
    for stock in stocks:
        if stock.code == stock_code:
            target_stock = stock
            break

    if not target_stock:
        print("등록되지 않은 종목코드입니다.")
        return

    disclosures = (
        db.query(Disclosure)
        .filter(Disclosure.stock_code == target_stock.code)
        .order_by(Disclosure.published_at.desc())
        .limit(30)
        .all()
    )

    if not disclosures:
        print("저장된 공시가 없습니다.")
        print("먼저 python scripts/collect_disclosures.py 를 실행하세요.")
        return

    disclosure_titles = [disclosure.title for disclosure in disclosures]
    result = score_disclosures(disclosure_titles)

    print()
    print(f"{target_stock.name}({target_stock.code}) 공시 점수")
    print("=" * 60)
    print(f"공시 개수: {len(disclosure_titles)}개")
    print(f"공시 점수: {result['score']}/100")

    print()
    print("[긍정 공시 키워드 감지]")
    if result["positive_matches"]:
        for item in result["positive_matches"]:
            print(f"- 키워드: {item['keyword']}")
            print(f"  제목: {item['title']}")
            print(f"  해석: {item['reason']}")
    else:
        print("- 없음")

    print()
    print("[위험 공시 키워드 감지]")
    if result["negative_matches"]:
        for item in result["negative_matches"]:
            print(f"- 키워드: {item['keyword']}")
            print(f"  제목: {item['title']}")
            print(f"  해석: {item['reason']}")
    else:
        print("- 없음")


if __name__ == "__main__":
    main()
