import sys
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.collectors.naver_news_collector import NaverNewsCollector
from app.config.rules_loader import load_theme_keywords
from app.database.connection import get_db
from app.services.candidate_stock_service import CandidateStockService
from app.services.stock_master_service import StockMasterService
from app.services.stock_service import StockService
from app.utils.text_cleaner import clean_html


def contains_any(text: str, keywords: list[str]) -> list[str]:
    matched = []

    for keyword in keywords:
        if keyword in text:
            matched.append(keyword)

    return matched


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


def main():
    db = get_db()

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

    news_collector = NaverNewsCollector()
    stock_master_service = StockMasterService(db)
    stock_service = StockService(db)
    candidate_service = CandidateStockService(db)

    stock_master_count = len(stock_master_service.get_all())

    if stock_master_count == 0:
        print("전체 상장 종목 목록이 없습니다.")
        print("먼저 python scripts/sync_stock_master.py 를 실행하세요.")
        return

    if not daily_keywords:
        print("daily 키워드가 없습니다.")
        print("app/config/theme_keywords.json 파일을 확인하세요.")
        return

    print("자동 테마 뉴스 스캔 시작")
    print("=" * 70)
    print(f"전체 상장 종목 수: {stock_master_count}개")
    print(f"검색 키워드 수: {len(daily_keywords)}개")
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

    saved_candidates = []

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

        saved_candidates.append(candidate)

    print()
    print("후보 저장 결과")
    print("=" * 70)
    print(f"저장/업데이트된 후보 수: {len(saved_candidates)}개")

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
        print("자동 등록 조건을 만족한 후보가 없습니다.")
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

    deleted_count = candidate_service.cleanup_old_candidates(
        days=auto_delete_after_days,
        min_score=auto_delete_score_below,
    )

    print()
    print("후보 자동 정리 결과")
    print("=" * 70)
    print(f"삭제된 오래된/저점수 후보 수: {deleted_count}개")

    print()
    print("최근 후보 TOP 20")
    print("=" * 70)

    recent_candidates = candidate_service.get_recent_candidates(limit=20)

    if not recent_candidates:
        print("저장된 후보가 없습니다.")
    else:
        for idx, candidate in enumerate(recent_candidates, start=1):
            print(
                f"[{idx}] {candidate.stock_name}({candidate.stock_code}) "
                f"/ score={candidate.score} "
                f"/ status={candidate.status} "
                f"/ news={candidate.news_count} "
                f"/ themes={candidate.theme_keyword_count} "
                f"/ risk={candidate.negative_keyword_count}"
            )

    print()
    print("자동 테마 뉴스 스캔 완료")


if __name__ == "__main__":
    main()
