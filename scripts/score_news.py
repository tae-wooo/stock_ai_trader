import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.analysis.scoring import score_news
from app.database.connection import get_db
from app.database.models import News
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

    stock_code = input("뉴스 점수를 계산할 종목코드 입력: ").strip()

    target_stock = None
    for stock in stocks:
        if stock.code == stock_code:
            target_stock = stock
            break

    if not target_stock:
        print("등록되지 않은 종목코드입니다.")
        return

    news_list = (
        db.query(News)
        .filter(News.stock_code == target_stock.code)
        .order_by(News.published_at.desc())
        .limit(30)
        .all()
    )

    if not news_list:
        print("저장된 뉴스가 없습니다.")
        print("먼저 python scripts/collect_news.py 를 실행하세요.")
        return

    news_titles = [news.title for news in news_list]
    result = score_news(news_titles)

    print()
    print(f"{target_stock.name}({target_stock.code}) 뉴스 점수")
    print("=" * 60)
    print(f"뉴스 개수: {len(news_titles)}개")
    print(f"뉴스 점수: {result['score']}/100")

    print()
    print("[긍정 키워드 감지]")
    if result["positive_matches"]:
        for item in result["positive_matches"]:
            print(f"- 키워드: {item['keyword']} / 제목: {item['title']}")
    else:
        print("- 없음")

    print()
    print("[부정 키워드 감지]")
    if result["negative_matches"]:
        for item in result["negative_matches"]:
            print(f"- 키워드: {item['keyword']} / 제목: {item['title']}")
    else:
        print("- 없음")


if __name__ == "__main__":
    main()
