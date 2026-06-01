import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import get_db
from app.services.price_service import PriceService
from app.services.stock_service import StockService


def main():
    db = get_db()

    stock_service = StockService(db)
    price_service = PriceService(db)

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

    stock_code = input("주가를 수집할 종목코드 입력: ").strip()

    target_stock = None
    for stock in stocks:
        if stock.code == stock_code:
            target_stock = stock
            break

    if not target_stock:
        print("등록되지 않은 종목코드입니다.")
        return

    days_input = input("최근 며칠치 수집할까요? 기본 60일, 그냥 엔터 가능: ").strip()

    days = 60
    if days_input:
        try:
            days = int(days_input)
        except ValueError:
            print("숫자가 아니라서 기본값 60일로 진행합니다.")
            days = 60

    print()
    print(f"주가 수집 시작: {target_stock.name}({target_stock.code}) / 최근 {days}일")

    try:
        price_service.collect_and_save(
            stock_code=target_stock.code,
            days=days,
        )

        print("주가 수집 완료")

    except Exception as e:
        print(f"주가 수집 실패: {e}")


if __name__ == "__main__":
    main()
