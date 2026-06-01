import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.ai.comparison_reporter import ComparisonReporter
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
from app.collectors.naver_news_collector import NaverNewsCollector
from app.config.rules_loader import load_theme_keywords, load_trade_rules
from app.database.connection import get_db
from app.database.models import CandidateStock, DailyPrice, Disclosure, News
from app.services.candidate_stock_service import CandidateStockService
from app.services.discord_service import DiscordService
from app.services.disclosure_service import DisclosureService
from app.services.news_service import NewsService
from app.services.price_service import PriceService
from app.services.stock_master_service import StockMasterService
from app.services.stock_service import StockService
from app.utils.text_cleaner import clean_html


def contains_any(text: str, keywords: list[str]) -> list[str]:
    matched = []

    for keyword in keywords:
        if keyword in text:
            matched.append(keyword)

    return matched


def make_safe_filename(text: str) -> str:
    return (
        text.replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace(":", "_")
    )


def save_text(content: str, folder: str, filename: str) -> Path:
    output_dir = ROOT_DIR / "reports" / folder
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


def calculate_candidate_score(
    title_matched: bool,
    description_matched: bool,
    news_count: int,
    theme_count: int,
    positive_count: int,
    negative_count: int,
    rules: dict,
) -> int:
    score = 0

    if title_matched:
        score += rules.get("title_match_score", 25)

    if description_matched:
        score += rules.get("description_match_score", 5)

    score += news_count * rules.get("news_count_score", 10)
    score += theme_count * rules.get("theme_keyword_score", 8)
    score += positive_count * rules.get("positive_keyword_score", 20)
    score -= negative_count * rules.get("negative_keyword_penalty", 50)

    return score


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


def get_latest_price_from_db(db, stock_code: str):
    latest_price = (
        db.query(DailyPrice)
        .filter(DailyPrice.stock_code == stock_code)
        .filter(DailyPrice.close_price.isnot(None))
        .order_by(DailyPrice.trade_date.desc())
        .first()
    )

    if not latest_price:
        return None

    return latest_price.close_price


def collect_price_for_filter(db, stock_code: str):
    price_service = PriceService(db)

    try:
        price_service.collect_and_save(
            stock_code=stock_code,
            days=30,
        )
    except Exception as e:
        print(f"- 가격 필터용 주가 수집 실패: {stock_code} / {e}")

    return get_latest_price_from_db(db, stock_code)


def is_price_allowed_for_candidate(
    current_price,
    max_price: int,
    skip_unknown_price: bool,
) -> tuple[bool, str]:
    if current_price is None:
        if skip_unknown_price:
            return False, "현재가 데이터가 없어 후보 등록에서 제외합니다."
        return True, "현재가 데이터가 없지만 설정상 후보 등록을 허용합니다."

    if current_price > max_price:
        return (
            False,
            f"현재가 {current_price:,.0f}원이 설정 한도 {max_price:,.0f}원을 초과하여 후보 등록에서 제외합니다.",
        )

    return True, f"현재가 {current_price:,.0f}원이 설정 한도 {max_price:,.0f}원 이하라 후보 등록을 허용합니다."


def send_no_action_notification(stats: dict):
    try:
        message = f"""
✅ **주식 AI 자동 파이프라인 실행 완료: 조건 만족 종목 없음**

오늘 뉴스 스캔은 정상 실행됐지만, 설정 조건을 만족해 AI 분석/알림을 보낼 종목은 없었습니다.

**실행 요약**
- 뉴스에서 감지된 종목 수: {stats.get("detected_count", 0)}개
- 점수 기준 통과 종목 수: {stats.get("score_passed_count", 0)}개
- 50,000원 이하 후보 통과 수: {stats.get("price_passed_count", 0)}개
- 가격 조건 초과/현재가 부족 제외 수: {stats.get("price_filtered_count", 0)}개
- 위험 키워드 차단 수: {stats.get("risk_blocked_count", 0)}개
- 신규 자동등록 수: {stats.get("auto_registered_count", 0)}개

OpenAI/Gemini 분석 API는 호출되지 않았습니다.
""".strip()

        discord_service = DiscordService()
        discord_service.send_message(message)

        print("- 조건 만족 종목 없음 Discord 알림 전송 완료")

    except Exception as e:
        print(f"- 조건 만족 종목 없음 Discord 알림 전송 실패: {e}")


def make_discord_message(file_path: Path, final_comparison: str) -> str:
    preview = final_comparison.strip()

    max_preview_length = 1400

    if len(preview) > max_preview_length:
        preview = preview[:max_preview_length].rstrip() + "\n..."

    message = f"""
📊 **주식 AI 최종 비교 리포트 생성 완료**

**파일명**
`{file_path.name}`

**핵심 미리보기**
{preview}

📎 전체 리포트는 첨부 파일을 확인하세요.
""".strip()

    if len(message) > 1900:
        message = message[:1900].rstrip() + "\n..."

    return message


def send_discord_notification(file_path: Path, final_comparison: str):
    try:
        discord_service = DiscordService()
        message = make_discord_message(file_path, final_comparison)

        discord_service.send_file_with_message(
            content=message,
            file_path=file_path,
        )

        print("- Discord 알림 전송 완료")

    except Exception as e:
        print(f"- Discord 알림 전송 실패: {e}")


def scan_theme_news_and_auto_register(db) -> dict:
    theme_config = load_theme_keywords()
    matching_rules = theme_config.get("matching_rules", {})

    daily_keywords = theme_config.get("priority", {}).get("daily", [])
    positive_keywords = theme_config.get("event_keywords", {}).get("positive", [])
    negative_keywords = theme_config.get("event_keywords", {}).get("negative", [])

    min_stock_name_length = matching_rules.get("min_stock_name_length", 3)
    ignore_stock_names = matching_rules.get("ignore_stock_names", [])
    min_candidate_score = matching_rules.get("min_candidate_score", 50)

    auto_register_score = matching_rules.get("auto_register_score", 80)
    auto_register_min_news_count = matching_rules.get("auto_register_min_news_count", 2)
    auto_register_min_theme_count = matching_rules.get("auto_register_min_theme_count", 2)
    max_auto_register_per_run = matching_rules.get("max_auto_register_per_run", 5)

    auto_delete_score_below = matching_rules.get("auto_delete_score_below", 40)
    auto_delete_after_days = matching_rules.get("auto_delete_after_days", 7)

    max_stock_price = matching_rules.get("max_stock_price_for_ai_analysis", 50000)
    skip_unknown_price = matching_rules.get("skip_ai_analysis_when_price_unknown", True)
    price_filter_pass_bonus = matching_rules.get("price_filter_pass_bonus", 15)

    news_collector = NaverNewsCollector()
    stock_master_service = StockMasterService(db)
    stock_service = StockService(db)
    candidate_service = CandidateStockService(db)

    stats = {
        "detected_count": 0,
        "score_passed_count": 0,
        "price_passed_count": 0,
        "price_filtered_count": 0,
        "risk_blocked_count": 0,
        "saved_candidate_count": 0,
        "auto_registered_count": 0,
        "deleted_count": 0,
    }

    stock_master_count = len(stock_master_service.get_all())

    if stock_master_count == 0:
        print("전체 상장 종목 목록이 없습니다.")
        print("먼저 python scripts/sync_stock_master.py 를 실행하세요.")
        return stats

    if not daily_keywords:
        print("daily 키워드가 없습니다.")
        print("app/config/theme_keywords.json 파일을 확인하세요.")
        return stats

    print()
    print("[1] 자동 테마 뉴스 스캔 시작")
    print("=" * 70)
    print(f"전체 상장 종목 수: {stock_master_count}개")
    print(f"검색 키워드 수: {len(daily_keywords)}개")
    print(f"후보 가격 기준: {max_stock_price:,.0f}원 이하")
    print(f"자동 등록 기준 점수: {auto_register_score}점 이상")
    print("=" * 70)

    detected = defaultdict(
        lambda: {
            "name": None,
            "code": None,
            "market": None,
            "theme_keywords": set(),
            "positive_keywords": set(),
            "negative_keywords": set(),
            "news_titles": set(),
            "title_matched": False,
            "description_matched": False,
        }
    )

    for keyword in daily_keywords:
        print(f"\n뉴스 검색 키워드: {keyword}")

        try:
            news_items = news_collector.search_news(
                keyword=keyword,
                display=10,
                sort="date",
            )
        except Exception as e:
            print(f"- 뉴스 검색 실패: {keyword} / {e}")
            continue

        print(f"- 뉴스 {len(news_items)}개 조회")

        for item in news_items:
            title = clean_html(item.get("title", ""))
            description = clean_html(item.get("description", ""))

            title_stocks = stock_master_service.find_by_name_in_text(
                text=title,
                min_name_length=min_stock_name_length,
                ignore_names=ignore_stock_names,
            )

            description_stocks = stock_master_service.find_by_name_in_text(
                text=description,
                min_name_length=min_stock_name_length,
                ignore_names=ignore_stock_names,
            )

            all_stocks = {}

            for stock_item in title_stocks:
                all_stocks[stock_item.code] = {
                    "stock": stock_item,
                    "title_matched": True,
                    "description_matched": False,
                }

            for stock_item in description_stocks:
                if stock_item.code in all_stocks:
                    all_stocks[stock_item.code]["description_matched"] = True
                else:
                    all_stocks[stock_item.code] = {
                        "stock": stock_item,
                        "title_matched": False,
                        "description_matched": True,
                    }

            if not all_stocks:
                continue

            text = f"{title} {description}"
            matched_positive = contains_any(text, positive_keywords)
            matched_negative = contains_any(text, negative_keywords)

            for stock_code, match_info in all_stocks.items():
                stock_item = match_info["stock"]
                data = detected[stock_code]

                data["name"] = stock_item.name
                data["code"] = stock_item.code
                data["market"] = stock_item.market
                data["theme_keywords"].add(keyword)

                if match_info["title_matched"]:
                    data["title_matched"] = True

                if match_info["description_matched"]:
                    data["description_matched"] = True

                for pk in matched_positive:
                    data["positive_keywords"].add(pk)

                for nk in matched_negative:
                    data["negative_keywords"].add(nk)

                if title:
                    data["news_titles"].add(title)

    stats["detected_count"] = len(detected)

    for stock_code, data in detected.items():
        news_titles = sorted(data["news_titles"])
        theme_keywords = sorted(data["theme_keywords"])
        positive = sorted(data["positive_keywords"])
        negative = sorted(data["negative_keywords"])

        score = calculate_candidate_score(
            title_matched=data["title_matched"],
            description_matched=data["description_matched"],
            news_count=len(news_titles),
            theme_count=len(theme_keywords),
            positive_count=len(positive),
            negative_count=len(negative),
            rules=matching_rules,
        )

        if score < min_candidate_score:
            continue

        stats["score_passed_count"] += 1

        current_price = collect_price_for_filter(db, data["code"])

        price_allowed, price_reason = is_price_allowed_for_candidate(
            current_price=current_price,
            max_price=max_stock_price,
            skip_unknown_price=skip_unknown_price,
        )

        if not price_allowed:
            candidate = candidate_service.upsert_candidate(
                stock_code=data["code"],
                stock_name=data["name"],
                market=data["market"],
                detected_keywords=theme_keywords,
                positive_keywords=positive,
                negative_keywords=negative,
                news_titles=news_titles,
                score=score,
            )
            candidate_service.mark_price_filtered(data["code"])
            stats["price_filtered_count"] += 1

            print(f"- 후보 제외: {data['name']}({data['code']}) / {price_reason}")
            continue

        score += price_filter_pass_bonus
        stats["price_passed_count"] += 1

        candidate = candidate_service.upsert_candidate(
            stock_code=data["code"],
            stock_name=data["name"],
            market=data["market"],
            detected_keywords=theme_keywords,
            positive_keywords=positive,
            negative_keywords=negative,
            news_titles=news_titles,
            score=score,
        )

        if negative:
            candidate_service.mark_risk_blocked(data["code"])
            stats["risk_blocked_count"] += 1
        else:
            candidate_service.mark_candidate(data["code"])
            stats["saved_candidate_count"] += 1

    print()
    print("후보 저장 결과")
    print("=" * 70)
    print(f"뉴스에서 감지된 종목 수: {stats['detected_count']}개")
    print(f"점수 기준 통과 종목 수: {stats['score_passed_count']}개")
    print(f"가격 조건 통과 종목 수: {stats['price_passed_count']}개")
    print(f"가격 조건 제외 종목 수: {stats['price_filtered_count']}개")
    print(f"후보 저장 종목 수: {stats['saved_candidate_count']}개")
    print(f"위험 차단 종목 수: {stats['risk_blocked_count']}개")

    auto_targets = candidate_service.get_auto_register_targets(
        min_score=auto_register_score,
        min_news_count=auto_register_min_news_count,
        min_theme_count=auto_register_min_theme_count,
        limit=max_auto_register_per_run,
    )

    print()
    print("자동 관심등록 대상")
    print("=" * 70)

    if not auto_targets:
        print("자동 등록 조건을 만족한 신규 후보가 없습니다.")
    else:
        for candidate in auto_targets:
            print(
                f"- {candidate.stock_name}({candidate.stock_code}) "
                f"/ score={candidate.score} "
                f"/ news={candidate.news_count} "
                f"/ themes={candidate.theme_keyword_count}"
            )

            stock_service.add_stock(
                code=candidate.stock_code,
                name=candidate.stock_name,
                market=candidate.market,
                sector="AUTO_THEME_CANDIDATE",
            )

            candidate_service.mark_auto_registered(candidate.stock_code)
            stats["auto_registered_count"] += 1

    deleted_count = candidate_service.cleanup_old_candidates(
        days=auto_delete_after_days,
        min_score=auto_delete_score_below,
    )

    stats["deleted_count"] = deleted_count

    print()
    print("후보 자동 정리 결과")
    print("=" * 70)
    print(f"삭제된 오래된/저점수 후보 수: {deleted_count}개")

    return stats


def get_auto_analysis_targets(db, limit: int) -> list[CandidateStock]:
    candidate_service = CandidateStockService(db)
    return candidate_service.get_auto_analysis_targets(limit=limit)


def collect_stock_data(
    stock_code: str,
    stock_name: str,
    news_service: NewsService,
    disclosure_service: DisclosureService,
    price_service: PriceService,
):
    print()
    print(f"[데이터 수집] {stock_name}({stock_code})")
    print("-" * 70)

    try:
        news_count = news_service.collect_and_save(
            stock_code=stock_code,
            keyword=stock_name,
            display=10,
        )
        print(f"- 뉴스 저장 완료: {news_count}개")
    except Exception as e:
        print(f"- 뉴스 수집 실패: {e}")

    try:
        disclosure_count = disclosure_service.collect_and_save(
            stock_code=stock_code,
            bgn_de="20240101",
        )
        print(f"- 공시 저장 완료: {disclosure_count}개")
    except Exception as e:
        print(f"- 공시 수집 실패: {e}")

    try:
        price_service.collect_and_save(
            stock_code=stock_code,
            days=120,
        )
        print("- 주가 수집 완료")
    except Exception as e:
        print(f"- 주가 수집 실패: {e}")


def analyze_stock(db, stock_code: str):
    prices = (
        db.query(DailyPrice)
        .filter(DailyPrice.stock_code == stock_code)
        .order_by(DailyPrice.trade_date.asc())
        .all()
    )

    news_list = (
        db.query(News)
        .filter(News.stock_code == stock_code)
        .order_by(News.published_at.desc())
        .limit(30)
        .all()
    )

    disclosures = (
        db.query(Disclosure)
        .filter(Disclosure.stock_code == stock_code)
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


def build_prompt(stock_name: str, stock_code: str, result: dict) -> str:
    theme_keywords = load_theme_keywords()
    trade_rules = load_trade_rules()

    return build_stock_analysis_prompt(
        stock_name=stock_name,
        stock_code=stock_code,
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
6. 사용자가 실제 진입을 고민할 수 있으므로 손절/익절 기준을 반드시 제시해라.
7. 매매 기준은 투자 추천이 아니라 리스크 관리 참고 기준으로만 제시해라.

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
10. 최종 참고 판단
11. 실전 대응 기준
   - 현재 상태:
   - 신규 진입 기준:
   - 진입하면 안 되는 조건:
   - 1차 익절 기준:
   - 2차 익절 기준:
   - 손절 기준:
   - 트레일링 스탑 기준:
   - 보유 중일 때 대응:
   - 한 줄 결론:
""".strip()


def run_ai_analysis_for_candidate(db, candidate: CandidateStock):
    candidate_service = CandidateStockService(db)

    news_service = NewsService(db)
    disclosure_service = DisclosureService(db)
    price_service = PriceService(db)

    stock_code = candidate.stock_code
    stock_name = candidate.stock_name

    print()
    print(f"[2] AI 분석 시작: {stock_name}({stock_code})")
    print("=" * 70)

    collect_stock_data(
        stock_code=stock_code,
        stock_name=stock_name,
        news_service=news_service,
        disclosure_service=disclosure_service,
        price_service=price_service,
    )

    result = analyze_stock(db, stock_code)

    print()
    print("[점수 요약]")
    print("-" * 70)
    print(f"- 현재가: {result['current_price']}")
    print(f"- 가격 점수: {result['price_score']}/100")
    print(f"- 뉴스 점수: {result['news_score']}/100")
    print(f"- 공시 점수: {result['disclosure_score']}/100")
    print(f"- 종합 점수: {result['total_score']}/100")
    print(f"- 판단: {result['judgment']}")

    prompt = build_prompt(
        stock_name=stock_name,
        stock_code=stock_code,
        result=result,
    )

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = make_safe_filename(stock_name)
    base_filename = f"{now}_{stock_code}_{safe_name}"

    prompt_path = save_text(
        content=prompt,
        folder="prompts",
        filename=f"{base_filename}_prompt.txt",
    )

    print()
    print(f"- 기본 프롬프트 저장: {prompt_path}")

    openai_report = None
    gemini_report = None

    try:
        openai_reporter = OpenAiReporter()
        openai_report = openai_reporter.generate_report(prompt)

        openai_path = save_text(
            content=openai_report,
            folder="ai_results",
            filename=f"{base_filename}_openai.txt",
        )

        print(f"- OpenAI 리포트 저장: {openai_path}")

    except Exception as e:
        print(f"- OpenAI 리포트 생성 실패: {e}")

    try:
        gemini_reporter = GeminiReporter()
        gemini_report = gemini_reporter.generate_report(prompt)

        gemini_path = save_text(
            content=gemini_report,
            folder="ai_results",
            filename=f"{base_filename}_gemini.txt",
        )

        print(f"- Gemini 리포트 저장: {gemini_path}")

    except Exception as e:
        print(f"- Gemini 리포트 생성 실패: {e}")

    if openai_report and gemini_report:
        comparison_prompt = build_comparison_prompt(
            stock_name=stock_name,
            stock_code=stock_code,
            openai_report=openai_report,
            gemini_report=gemini_report,
        )

        comparison_path = save_text(
            content=comparison_prompt,
            folder="comparisons",
            filename=f"{base_filename}_comparison_prompt.txt",
        )

        print(f"- 비교 프롬프트 저장: {comparison_path}")

        try:
            comparison_reporter = ComparisonReporter()
            final_comparison = comparison_reporter.generate_comparison(comparison_prompt)

            final_comparison_path = save_text(
                content=final_comparison,
                folder="final_comparisons",
                filename=f"{base_filename}_final_comparison.txt",
            )

            print(f"- 최종 비교 리포트 저장: {final_comparison_path}")

            send_discord_notification(
                file_path=final_comparison_path,
                final_comparison=final_comparison,
            )

        except Exception as e:
            print(f"- 최종 비교 리포트 생성 실패: {e}")
            print("- OpenAI/Gemini 개별 리포트와 비교 프롬프트는 저장되어 있습니다.")

        candidate_service.mark_ai_analyzed(stock_code)
        print("- 후보 상태 변경: AI_ANALYZED")

    else:
        print("- 비교 프롬프트 생성 생략: OpenAI 또는 Gemini 결과가 없습니다.")
        print("- 후보 상태는 AUTO_REGISTERED로 유지됩니다. 다음 실행 때 다시 분석할 수 있습니다.")


def main():
    db = get_db()

    theme_config = load_theme_keywords()
    matching_rules = theme_config.get("matching_rules", {})
    max_ai_analysis_per_run = matching_rules.get("max_ai_analysis_per_run", 3)

    print()
    print("완전 자동 주식 AI 파이프라인 시작")
    print("=" * 70)

    scan_stats = scan_theme_news_and_auto_register(db)

    targets = get_auto_analysis_targets(
        db=db,
        limit=max_ai_analysis_per_run,
    )

    print()
    print("[2] 자동 AI 분석 대상")
    print("=" * 70)

    if not targets:
        print("자동 AI 분석 대상이 없습니다.")
        print("조건을 만족한 50,000원 이하 AUTO_REGISTERED 후보가 없습니다.")

        send_no_action_notification(scan_stats)
        return

    for index, target in enumerate(targets, start=1):
        print(
            f"[{index}] {target.stock_name}({target.stock_code}) "
            f"/ score={target.score} "
            f"/ news={target.news_count} "
            f"/ themes={target.theme_keyword_count} "
            f"/ status={target.status}"
        )

    for target in targets:
        run_ai_analysis_for_candidate(db=db, candidate=target)

    print()
    print("완전 자동 주식 AI 파이프라인 완료")
    print("=" * 70)
    print("결과 파일은 reports/ 폴더에서 확인할 수 있습니다.")


if __name__ == "__main__":
    main()
