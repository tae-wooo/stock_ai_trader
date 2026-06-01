import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import get_db
from app.services.stock_service import StockService


def main():
    db = get_db()
    stock_service = StockService(db)

    stocks = stock_service.get_all_stocks()

    if not stocks:
        print("등록된 관심종목이 없습니다.")
        return

    print("등록된 관심종목")
    print("-" * 40)

    for stock in stocks:
        market_text = stock.market if stock.market else "-"
        sector_text = stock.sector if stock.sector else "-"
        print(f"{stock.id}. {stock.name}({stock.code}) / {market_text} / {sector_text}")

    print("-" * 40)

    code = input("삭제할 종목코드 입력: ").strip()

    target_stock = None
    for stock in stocks:
        if stock.code == code:
            target_stock = stock
            break

    if not target_stock:
        print("등록되지 않은 종목코드입니다.")
        return

    print()
    print(f"삭제 대상: {target_stock.name}({target_stock.code})")
    confirm = input("정말 삭제할까요? y/N: ").strip().lower()

    if confirm != "y":
        print("삭제를 취소했습니다.")
        return

    deleted = stock_service.delete_stock(code)

    if deleted:
        print(f"삭제 완료: {target_stock.name}({target_stock.code})")
    else:
        print("삭제 실패: 종목을 찾을 수 없습니다.")


if __name__ == "__main__":
    main()
