import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import get_db
from app.services.stock_service import StockService


def main():
    db = get_db()
    stock_service = StockService(db)

    print("관심종목 등록")
    print("-" * 30)

    code = input("종목코드 입력 예: 005930: ").strip()
    name = input("종목명 입력 예: 삼성전자: ").strip()
    market = input("시장 입력 예: KOSPI/KOSDAQ, 모르면 엔터: ").strip()
    sector = input("섹터 입력 예: 반도체/AI/바이오, 모르면 엔터: ").strip()

    stock_service.add_stock(
        code=code,
        name=name,
        market=market if market else None,
        sector=sector if sector else None,
    )

    print()
    print("현재 등록된 관심종목")
    print("-" * 30)

    stocks = stock_service.get_all_stocks()

    if not stocks:
        print("등록된 종목이 없습니다.")
        return

    for stock in stocks:
        market_text = stock.market if stock.market else "-"
        sector_text = stock.sector if stock.sector else "-"
        print(f"{stock.id}. {stock.name}({stock.code}) / {market_text} / {sector_text}")


if __name__ == "__main__":
    main()
