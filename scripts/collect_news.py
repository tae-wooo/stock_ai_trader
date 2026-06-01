import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import get_db
from app.services.news_service import NewsService
from app.services.stock_service import StockService


def main():
    db = get_db()

    stock_service = StockService(db)
    news_service = NewsService(db)

    stocks = stock_service.get_all_stocks()

    if not stocks:
        print("등록된 관심종목이 없습니다.")
        print("먼저 python scripts/add_stock.py 로 종목을 등록하세요.")
        return

    print("등록된 관심종목")
    print("-" * 30)

    for stock in stocks:
        print(f"{stock.id}. {stock.name}({stock.code})")

    print("-" * 30)

    stock_code = input("뉴스를 수집할 종목코드 입력: ").strip()

    target_stock = None
    for stock in stocks:
        if stock.code == stock_code:
            target_stock = stock
            break

    if not target_stock:
        print("등록되지 않은 종목코드입니다.")
        return

    print(f"\n뉴스 수집 시작: {target_stock.name}({target_stock.code})")

    try:
        saved_count = news_service.collect_and_save(
            stock_code=target_stock.code,
            keyword=target_stock.name,
            display=10,
        )

        print(f"뉴스 저장 완료: {saved_count}개")

    except Exception as e:
        print(f"뉴스 수집 실패: {e}")


if __name__ == "__main__":
    main()
