import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.analysis.scoring import score_news
from app.analysis.disclosure_scoring import score_disclosures
from app.analysis.technical_indicator import (
    calculate_moving_average,
    calculate_recent_return,
    calculate_volume_ratio,
    score_price,
)
from app.database.connection import get_db
from app.database.models import News, Disclosure, DailyPrice
from app.services.stock_service import StockService


def judge_score(total_score: int) -> str:
    if total_score >= 80:
        return "강한 관심 후보"
    if total_score >= 65:
        return "관심 후보"
    if total_score >= 50:
        return "중립 / 관망"
    if total_score >= 35:
        return "주의 필요"
    return "위험"


def calculate_total_score(price_score: int, news_score: int, disclosure_score: int) -> int:
    total_score = (
        price_score * 0.4
        + news_score * 0.3
        + disclosure_score * 0.3
    )

    return round(total_score)


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

    stock_code = input("종합 점수를 계산할 종목코드 입력: ").strip()

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
        .order_by(DailyPrice.trade_date.asc())
        .all()
    )

    news_list = (
        db.query(News)
        .filter(News.stock_code == target_stock.code)
        .order_by(News.published_at.desc())
        .limit(30)
        .all()
    )

    disclosures = (
        db.query(Disclosure)
        .filter(Disclosure.stock_code == target_stock.code)
        .order_by(Disclosure.published_at.desc())
        .limit(30)
        .all()
    )

    close_prices = [price.close_price for price in prices if price.close_price is not None]
    volumes = [price.volume for price in prices if price.volume is not None]

    if len(close_prices) >= 21:
        current_price = close_prices[-1]
        return_5d = calculate_recent_return(close_prices, 5)
        return_20d = calculate_recent_return(close_prices, 20)
        ma20 = calculate_moving_average(close_prices, 20)
        volume_ratio = calculate_volume_ratio(volumes, 20)

        price_result = score_price(
            return_5d=return_5d,
            return_20d=return_20d,
            current_price=current_price,
            ma20=ma20,
            volume_ratio=volume_ratio,
        )

        price_score = price_result["score"]
        price_reasons = price_result["reasons"]

    else:
        current_price = None
        return_5d = None
        return_20d = None
        ma20 = None
        volume_ratio = None
        price_score = 50
        price_reasons = ["주가 데이터가 부족해서 가격 점수는 기본값 50점으로 처리했습니다."]

    news_titles = [news.title for news in news_list]
    disclosure_titles = [disclosure.title for disclosure in disclosures]

    news_result = score_news(news_titles)
    disclosure_result = score_disclosures(disclosure_titles)

    news_score = news_result["score"]
    disclosure_score = disclosure_result["score"]

    total_score = calculate_total_score(
        price_score=price_score,
        news_score=news_score,
        disclosure_score=disclosure_score,
    )

    judgment = judge_score(total_score)

    print()
    print(f"{target_stock.name}({target_stock.code}) 종합 분석")
    print("=" * 70)

    print("[데이터 개수]")
    print(f"- 주가 데이터: {len(close_prices)}개")
    print(f"- 뉴스 데이터: {len(news_titles)}개")
    print(f"- 공시 데이터: {len(disclosure_titles)}개")

    print()
    print("[가격 지표]")
    if current_price is not None:
        print(f"- 현재가: {current_price:,.0f}원")
    else:
        print("- 현재가: 데이터 부족")

    print(f"- 5일 수익률: {return_5d if return_5d is not None else '데이터 부족'}%")
    print(f"- 20일 수익률: {return_20d if return_20d is not None else '데이터 부족'}%")

    if ma20 is not None:
        print(f"- 20일 이동평균: {ma20:,.0f}원")
    else:
        print("- 20일 이동평균: 데이터 부족")

    print(f"- 거래량 비율: {volume_ratio if volume_ratio is not None else '데이터 부족'}배")

    print()
    print("[점수]")
    print(f"- 가격 점수: {price_score}/100")
    print(f"- 뉴스 점수: {news_score}/100")
    print(f"- 공시 점수: {disclosure_score}/100")
    print("-" * 70)
    print(f"- 종합 점수: {total_score}/100")
    print(f"- 판단: {judgment}")
    print()
    print("[점수 판단 기준]")
    print("- 80점 이상: 강한 관심 후보")
    print("- 65점 이상: 관심 후보")
    print("- 50점 이상: 중립 / 관망")
    print("- 35점 이상: 주의 필요")
    print("- 35점 미만: 위험")

    print()
    print("[가격 점수 근거]")
    if price_reasons:
        for reason in price_reasons:
            print(f"- {reason}")
    else:
        print("- 특별한 가격 신호가 없습니다.")

    print()
    print("[뉴스 긍정 키워드]")
    if news_result["positive_matches"]:
        for item in news_result["positive_matches"][:5]:
            print(f"- {item['keyword']} / {item['title']}")
    else:
        print("- 없음")

    print()
    print("[뉴스 부정 키워드]")
    if news_result["negative_matches"]:
        for item in news_result["negative_matches"][:5]:
            print(f"- {item['keyword']} / {item['title']}")
    else:
        print("- 없음")

    print()
    print("[공시 긍정 키워드]")
    if disclosure_result["positive_matches"]:
        for item in disclosure_result["positive_matches"][:5]:
            print(f"- {item['keyword']} / {item['title']}")
    else:
        print("- 없음")

    print()
    print("[공시 위험 키워드]")
    if disclosure_result["negative_matches"]:
        for item in disclosure_result["negative_matches"][:5]:
            print(f"- {item['keyword']} / {item['title']}")
    else:
        print("- 없음")


if __name__ == "__main__":
    main()
