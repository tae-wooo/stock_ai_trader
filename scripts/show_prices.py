import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import get_db
from app.database.models import DailyPrice
from app.services.stock_service import StockService


def format_number(value):
    if value is None:
        return "-"
    return f"{int(value):,}"


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

    stock_code = input("주가를 확인할 종목코드 입력: ").strip()

    target_stock = None
    for stock in stocks:
        if stock.code == stock_code:
            target_stock = stock
            break

    if not target_stock:
        print("등록되지 않은 종목코드입니다.")
        return

    prices = (
        db.query(DailyPrice)
        .filter(DailyPrice.stock_code == target_stock.code)
        .order_by(DailyPrice.trade_date.desc())
        .limit(20)
        .all()
    )

    print()
    print(f"{target_stock.name}({target_stock.code}) 저장된 주가 데이터")
    print("=" * 90)

    if not prices:
        print("저장된 주가 데이터가 없습니다.")
        print("먼저 python scripts/collect_prices.py 를 실행하세요.")
        return

    print(f"{'날짜':<12} {'시가':>10} {'고가':>10} {'저가':>10} {'종가':>10} {'거래량':>15} {'등락률':>10}")
    print("-" * 90)

    for price in prices:
        change_rate = "-"
        if price.change_rate is not None:
            change_rate = f"{price.change_rate:.2f}%"

        print(
            f"{str(price.trade_date):<12} "
            f"{format_number(price.open_price):>10} "
            f"{format_number(price.high_price):>10} "
            f"{format_number(price.low_price):>10} "
            f"{format_number(price.close_price):>10} "
            f"{format_number(price.volume):>15} "
            f"{change_rate:>10}"
        )


if __name__ == "__main__":
    main()
