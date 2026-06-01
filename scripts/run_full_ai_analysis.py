import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.ai.gemini_reporter import GeminiReporter
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
from app.services.disclosure_service import DisclosureService
from app.services.news_service import NewsService
from app.services.price_service import PriceService
from app.services.stock_service import StockService
from app.config.rules_loader import load_theme_keywords, load_trade_rules

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
    return round(price_score * 0.4 + news_score * 0.3 + disclosure_score * 0.3)


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

    stock_code = input("전체 AI 분석을 실행할 종목코드 입력: ").strip()

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

    return {
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


def build_prompt(target_stock, result: dict) -> str:
    theme_keywords = load_theme_keywords()
    trade_rules = load_trade_rules()

    return build_stock_analysis_prompt(
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
        theme_keywords=theme_keywords,
        trade_rules=trade_rules,
    )


def save_text(content: str, folder: str, filename: str) -> Path:
    output_dir = ROOT_DIR / "reports" / folder
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


def print_analysis_summary(target_stock, result: dict):
    print()
    print(f"{target_stock.name}({target_stock.code}) 종합 분석")
    print("=" * 70)

    print("[데이터 개수]")
    print(f"- 주가 데이터: {result['price_count']}개")
    print(f"- 뉴스 데이터: {result['news_count']}개")
    print(f"- 공시 데이터: {result['disclosure_count']}개")

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


def build_comparison_prompt(
    stock_name: str,
    stock_code: str,
    openai_report: str,
    gemini_report: str,
) -> str:
    return f"""
너는 신중한 투자 분석 검토자다.

아래에는 같은 종목에 대해 두 AI가 작성한 분석 리포트가 있다.
두 리포트를 비교해서, 어느 쪽이 더 신중하고 데이터에 충실한지 평가해라.

중요 규칙:
1. 제공된 두 리포트 내용만 근거로 비교해라.
2. 근거 없는 확정 표현은 피하라.
3. 매수/매도 추천을 단정하지 말고 리스크를 함께 설명해라.
4. 초보자도 이해할 수 있게 쉽게 정리해라.
5. 두 AI가 모두 놓친 위험 요소가 있으면 따로 지적해라.

[종목]
- 종목명: {stock_name}
- 종목코드: {stock_code}

[OpenAI 리포트]
{openai_report}

[Gemini 리포트]
{gemini_report}

아래 형식으로 비교 결과를 작성해라.

1. 두 AI의 공통 의견
2. 두 AI의 차이점
3. OpenAI 리포트의 장점
4. Gemini 리포트의 장점
5. OpenAI 리포트의 아쉬운 점
6. Gemini 리포트의 아쉬운 점
7. 더 보수적인 판단을 한 쪽
8. 더 설득력 있는 판단을 한 쪽
9. 초보자가 최종적으로 참고해야 할 핵심 포인트
10. 최종 참고 판단: 강한 관심 후보 / 관심 후보 / 중립 / 주의 필요 / 위험 / 데이터 부족 중 하나
""".strip()


def main():
    db = get_db()

    stock_service = StockService(db)
    news_service = NewsService(db)
    disclosure_service = DisclosureService(db)
    price_service = PriceService(db)

    target_stock = select_stock(stock_service)

    if not target_stock:
        return

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = make_safe_filename(target_stock.name)
    base_filename = f"{now}_{target_stock.code}_{safe_name}"

    print()
    print(f"전체 AI 분석 시작: {target_stock.name}({target_stock.code})")
    print("=" * 70)

    collect_data(
        stock_code=target_stock.code,
        stock_name=target_stock.name,
        news_service=news_service,
        disclosure_service=disclosure_service,
        price_service=price_service,
    )

    result = analyze_stock(db, target_stock)
    print_analysis_summary(target_stock, result)

    prompt = build_prompt(target_stock, result)

    prompt_path = save_text(
        content=prompt,
        folder="prompts",
        filename=f"{base_filename}_prompt.txt",
    )

    print()
    print("[4] 기본 분석 프롬프트 저장 완료")
    print(f"- {prompt_path}")

    openai_report = None
    gemini_report = None

    print()
    print("[5] OpenAI 리포트 생성 시작")

    try:
        openai_reporter = OpenAiReporter()
        openai_report = openai_reporter.generate_report(prompt)

        openai_path = save_text(
            content=openai_report,
            folder="ai_results",
            filename=f"{base_filename}_openai.txt",
        )

        print("OpenAI 리포트 저장 완료")
        print(f"- {openai_path}")

    except Exception as e:
        print(f"OpenAI 리포트 생성 실패: {e}")

    print()
    print("[6] Gemini 리포트 생성 시작")

    try:
        gemini_reporter = GeminiReporter()
        gemini_report = gemini_reporter.generate_report(prompt)

        gemini_path = save_text(
            content=gemini_report,
            folder="ai_results",
            filename=f"{base_filename}_gemini.txt",
        )

        print("Gemini 리포트 저장 완료")
        print(f"- {gemini_path}")

    except Exception as e:
        print(f"Gemini 리포트 생성 실패: {e}")

    if openai_report and gemini_report:
        print()
        print("[7] OpenAI vs Gemini 비교 프롬프트 생성 시작")

        comparison_prompt = build_comparison_prompt(
            stock_name=target_stock.name,
            stock_code=target_stock.code,
            openai_report=openai_report,
            gemini_report=gemini_report,
        )

        comparison_path = save_text(
            content=comparison_prompt,
            folder="comparisons",
            filename=f"{base_filename}_comparison_prompt.txt",
        )

        print("비교 프롬프트 저장 완료")
        print(f"- {comparison_path}")

    else:
        print()
        print("[7] 비교 프롬프트 생성 생략")
        print("OpenAI 또는 Gemini 리포트 중 하나가 생성되지 않았습니다.")

    print()
    print("전체 AI 분석 완료")
    print("=" * 70)
    print("생성된 파일은 reports/ 폴더에서 확인할 수 있습니다.")


if __name__ == "__main__":
    main()
