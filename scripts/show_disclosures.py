import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

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

    stock_code = input("공시를 확인할 종목코드 입력: ").strip()

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

    print()
    print(f"{target_stock.name}({target_stock.code}) 저장된 공시")
    print("=" * 70)

    if not disclosures:
        print("저장된 공시가 없습니다.")
        print("먼저 python scripts/collect_disclosures.py 를 실행하세요.")
        return

    for index, disclosure in enumerate(disclosures, start=1):
        print(f"\n[{index}] {disclosure.title}")
        print(f"날짜: {disclosure.published_at if disclosure.published_at else '-'}")
        print(f"접수번호: {disclosure.report_no}")
        print(f"링크: {disclosure.dart_url}")
        print("-" * 70)


if __name__ == "__main__":
    main()
