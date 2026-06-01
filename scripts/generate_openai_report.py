import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.ai.openai_reporter import OpenAiReporter
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

    stock_code = input("OpenAI 리포트를 생성할 종목코드 입력: ").strip()

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

    close_prices = [
        price.close_price
        for price in prices
        if price.close_price is not None
    ]

    volumes = [
        price.volume
        for price in prices
        if price.volume is not None
    ]

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
        price_reasons = [
            "주가 데이터가 부족해서 가격 점수는 기본값 50점으로 처리했습니다."
        ]

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

    prompt = build_stock_analysis_prompt(
        stock_name=target_stock.name,
        stock_code=target_stock.code,
        current_price=current_price,
        return_5d=return_5d,
        return_20d=return_20d,
        ma20=ma20,
        volume_ratio=volume_ratio,
        price_score=price_score,
        news_score=news_score,
        disclosure_score=disclosure_score,
        total_score=total_score,
        judgment=judgment,
        news_titles=news_titles,
        disclosure_titles=disclosure_titles,
        price_reasons=price_reasons,
        news_positive_matches=news_result["positive_matches"],
        news_negative_matches=news_result["negative_matches"],
        disclosure_positive_matches=disclosure_result["positive_matches"],
        disclosure_negative_matches=disclosure_result["negative_matches"],
    )

    print()
    print(f"{target_stock.name}({target_stock.code}) OpenAI 리포트 생성 중...")
    print("=" * 70)

    try:
        reporter = OpenAiReporter()
        report = reporter.generate_report(prompt)

        print(report)

        output_dir = ROOT_DIR / "reports" / "ai_results"
        output_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = make_safe_filename(target_stock.name)

        output_path = output_dir / f"{now}_{target_stock.code}_{safe_name}_openai.txt"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

        print()
        print("OpenAI 리포트 저장 완료")
        print(f"파일 위치: {output_path}")

    except Exception as e:
        print(f"OpenAI 리포트 생성 실패: {e}")


if __name__ == "__main__":
    main()
