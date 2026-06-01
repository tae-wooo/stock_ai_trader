import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.ai.prompt_builder import build_stock_analysis_prompt
from app.analysis.disclosure_scoring import score_disclosures
from app.analysis.scoring import score_news
from app.analysis.technical_indicator import (
    calculate_moving_average,
    calculate_recent_return,
    calculate_volume_ratio,
    score_price,
)
from app.database.connection import get_db
from app.database.models import DailyPrice, Disclosure, News
from app.services.disclosure_service import DisclosureService
from app.services.news_service import NewsService
from app.services.price_service import PriceService
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
    return round(
        price_score * 0.4
        + news_score * 0.3
        + disclosure_score * 0.3
    )


def make_safe_filename(text: str) -> str:
    return (
        text.replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace(":", "_")
    )


def select_stock(stock_service: StockService):
    stocks = stock_service.get_all_stocks()

    if not stocks:
        print("등록된 관심종목이 없습니다.")
        print("먼저 python scripts/add_stock.py 로 종목을 등록하세요.")
        return None

    print("등록된 관심종목")
    print("-" * 40)

    for stock in stocks:
        market_text = stock.market if stock.market else "-"
        sector_text = stock.sector if stock.sector else "-"
        print(f"{stock.id}. {stock.name}({stock.code}) / {market_text} / {sector_text}")

    print("-" * 40)

    stock_code = input("분석할 종목코드 입력: ").strip()

    for stock in stocks:
        if stock.code == stock_code:
            return stock

    print("등록되지 않은 종목코드입니다.")
    return None


def collect_data(
    stock_code: str,
    stock_name: str,
    news_service: NewsService,
    disclosure_service: DisclosureService,
    price_service: PriceService,
):
    print()
    print(f"[1] 뉴스 수집 시작: {stock_name}({stock_code})")
    try:
        news_count = news_service.collect_and_save(
            stock_code=stock_code,
            keyword=stock_name,
            display=10,
        )
        print(f"뉴스 저장 완료: {news_count}개")
    except Exception as e:
        print(f"뉴스 수집 실패: {e}")

    print()
    print(f"[2] 공시 수집 시작: {stock_name}({stock_code})")
    try:
        disclosure_count = disclosure_service.collect_and_save(
            stock_code=stock_code,
            bgn_de="20240101",
        )
        print(f"공시 저장 완료: {disclosure_count}개")
    except Exception as e:
        print(f"공시 수집 실패: {e}")

    print()
    print(f"[3] 주가 수집 시작: {stock_name}({stock_code})")
    try:
        price_service.collect_and_save(
            stock_code=stock_code,
            days=120,
        )
        print("주가 수집 완료")
    except Exception as e:
        print(f"주가 수집 실패: {e}")


def analyze_stock(db, target_stock):
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

    result = {
        "current_price": current_price,
        "return_5d": return_5d,
        "return_20d": return_20d,
        "ma20": ma20,
        "volume_ratio": volume_ratio,
        "price_score": price_score,
        "news_score": news_score,
        "disclosure_score": disclosure_score,
        "total_score": total_score,
        "judgment": judgment,
        "news_titles": news_titles,
        "disclosure_titles": disclosure_titles,
        "price_reasons": price_reasons,
        "news_result": news_result,
        "disclosure_result": disclosure_result,
        "price_count": len(close_prices),
        "news_count": len(news_titles),
        "disclosure_count": len(disclosure_titles),
    }

    return result


def print_analysis_result(target_stock, result: dict):
    print()
    print(f"{target_stock.name}({target_stock.code}) 종합 분석")
    print("=" * 70)

    print("[데이터 개수]")
    print(f"- 주가 데이터: {result['price_count']}개")
    print(f"- 뉴스 데이터: {result['news_count']}개")
    print(f"- 공시 데이터: {result['disclosure_count']}개")

    print()
    print("[가격 지표]")

    if result["current_price"] is not None:
        print(f"- 현재가: {result['current_price']:,.0f}원")
    else:
        print("- 현재가: 데이터 부족")

    print(f"- 5일 수익률: {result['return_5d'] if result['return_5d'] is not None else '데이터 부족'}%")
    print(f"- 20일 수익률: {result['return_20d'] if result['return_20d'] is not None else '데이터 부족'}%")

    if result["ma20"] is not None:
        print(f"- 20일 이동평균: {result['ma20']:,.0f}원")
    else:
        print("- 20일 이동평균: 데이터 부족")

    print(f"- 거래량 비율: {result['volume_ratio'] if result['volume_ratio'] is not None else '데이터 부족'}배")

    print()
    print("[점수]")
    print(f"- 가격 점수: {result['price_score']}/100")
    print(f"- 뉴스 점수: {result['news_score']}/100")
    print(f"- 공시 점수: {result['disclosure_score']}/100")
    print("-" * 70)
    print(f"- 종합 점수: {result['total_score']}/100")
    print(f"- 판단: {result['judgment']}")

    print()
    print("[점수 판단 기준]")
    print("- 80점 이상: 강한 관심 후보")
    print("- 65점 이상: 관심 후보")
    print("- 50점 이상: 중립 / 관망")
    print("- 35점 이상: 주의 필요")
    print("- 35점 미만: 위험")

    print()
    print("[가격 점수 근거]")
    if result["price_reasons"]:
        for reason in result["price_reasons"]:
            print(f"- {reason}")
    else:
        print("- 특별한 가격 신호가 없습니다.")

    print()
    print("[뉴스 긍정 키워드]")
    if result["news_result"]["positive_matches"]:
        for item in result["news_result"]["positive_matches"][:5]:
            print(f"- {item['keyword']} / {item['title']}")
    else:
        print("- 없음")

    print()
    print("[뉴스 부정 키워드]")
    if result["news_result"]["negative_matches"]:
        for item in result["news_result"]["negative_matches"][:5]:
            print(f"- {item['keyword']} / {item['title']}")
    else:
        print("- 없음")

    print()
    print("[공시 긍정 키워드]")
    if result["disclosure_result"]["positive_matches"]:
        for item in result["disclosure_result"]["positive_matches"][:5]:
            print(f"- {item['keyword']} / {item['title']}")
    else:
        print("- 없음")

    print()
    print("[공시 위험 키워드]")
    if result["disclosure_result"]["negative_matches"]:
        for item in result["disclosure_result"]["negative_matches"][:5]:
            print(f"- {item['keyword']} / {item['title']}")
    else:
        print("- 없음")


def save_prompt(target_stock, result: dict) -> Path:
    prompt = build_stock_analysis_prompt(
        stock_name=target_stock.name,
        stock_code=target_stock.code,
        current_price=result["current_price"],
        return_5d=result["return_5d"],
        return_20d=result["return_20d"],
        ma20=result["ma20"],
        volume_ratio=result["volume_ratio"],
        price_score=result["price_score"],
        news_score=result["news_score"],
        disclosure_score=result["disclosure_score"],
        total_score=result["total_score"],
        judgment=result["judgment"],
        news_titles=result["news_titles"],
        disclosure_titles=result["disclosure_titles"],
        price_reasons=result["price_reasons"],
        news_positive_matches=result["news_result"]["positive_matches"],
        news_negative_matches=result["news_result"]["negative_matches"],
        disclosure_positive_matches=result["disclosure_result"]["positive_matches"],
        disclosure_negative_matches=result["disclosure_result"]["negative_matches"],
    )

    output_dir = ROOT_DIR / "reports" / "prompts"
    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = make_safe_filename(target_stock.name)

    output_path = output_dir / f"{now}_{target_stock.code}_{safe_name}_prompt.txt"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    return output_path


def main():
    db = get_db()

    stock_service = StockService(db)
    news_service = NewsService(db)
    disclosure_service = DisclosureService(db)
    price_service = PriceService(db)

    target_stock = select_stock(stock_service)

    if not target_stock:
        return

    print()
    print(f"분석 대상: {target_stock.name}({target_stock.code})")
    print("=" * 70)

    collect_data(
        stock_code=target_stock.code,
        stock_name=target_stock.name,
        news_service=news_service,
        disclosure_service=disclosure_service,
        price_service=price_service,
    )

    result = analyze_stock(db, target_stock)

    print_analysis_result(target_stock, result)

    output_path = save_prompt(target_stock, result)

    print()
    print("AI 프롬프트 파일 저장 완료")
    print("=" * 70)
    print(f"파일 위치: {output_path}")
    print()
    print("이 파일을 열어서 전체 복사한 뒤 ChatGPT와 Gemini에 각각 붙여넣으면 됩니다.")


if __name__ == "__main__":
    main()
