import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import get_db
from app.services.disclosure_service import DisclosureService
from app.services.stock_service import StockService


def main():
    db = get_db()

    stock_service = StockService(db)
    disclosure_service = DisclosureService(db)

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

    stock_code = input("공시를 수집할 종목코드 입력: ").strip()

    target_stock = None
    for stock in stocks:
        if stock.code == stock_code:
            target_stock = stock
            break

    if not target_stock:
        print("등록되지 않은 종목코드입니다.")
        return

    print()
    print(f"공시 수집 시작: {target_stock.name}({target_stock.code})")

    try:
        saved_count = disclosure_service.collect_and_save(
        stock_code=target_stock.code,
        bgn_de="20240101",
    )

        print(f"공시 저장 완료: {saved_count}개")

    except Exception as e:
        print(f"공시 수집 실패: {e}")


if __name__ == "__main__":
    main()
