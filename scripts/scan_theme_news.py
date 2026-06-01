import sys
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.collectors.naver_news_collector import NaverNewsCollector
from app.config.rules_loader import load_theme_keywords
from app.database.connection import get_db
from app.services.stock_master_service import StockMasterService
from app.services.stock_service import StockService
from app.utils.text_cleaner import clean_html


def contains_any(text: str, keywords: list[str]) -> list[str]:
    matched = []

    for keyword in keywords:
        if keyword in text:
            matched.append(keyword)

    return matched


def main():
    db = get_db()

    theme_config = load_theme_keywords()

    daily_keywords = theme_config.get("priority", {}).get("daily", [])
    positive_keywords = theme_config.get("event_keywords", {}).get("positive", [])
    negative_keywords = theme_config.get("event_keywords", {}).get("negative", [])

    matching_rules = theme_config.get("matching_rules", {})
    min_stock_name_length = matching_rules.get("min_stock_name_length", 3)
    ignore_stock_names = matching_rules.get("ignore_stock_names", [])
    min_candidate_score = matching_rules.get("min_candidate_score", 40)

    news_collector = NaverNewsCollector()
    stock_master_service = StockMasterService(db)
    stock_service = StockService(db)

    stock_master_count = len(stock_master_service.get_all())

    if stock_master_count == 0:
        print("전체 상장 종목 목록이 없습니다.")
        print("먼저 아래 명령어를 실행하세요.")
        print("python scripts/sync_stock_master.py")
        return

    if not daily_keywords:
        print("daily 키워드가 없습니다.")
        print("app/config/theme_keywords.json 파일의 priority.daily를 확인하세요.")
        return

    candidates = defaultdict(
        lambda: {
            "name": None,
            "code": None,
            "market": None,
            "matched_theme_keywords": set(),
            "matched_positive_keywords": set(),
            "matched_negative_keywords": set(),
            "news_titles": [],
            "score": 0,
        }
    )

    print("테마 뉴스 스캔 시작")
    print("=" * 70)
    print(f"전체 상장 종목 수: {stock_master_count}개")
    print(f"검색 키워드 수: {len(daily_keywords)}개")
    print("=" * 70)

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
            raw_title = item.get("title", "")
            raw_description = item.get("description", "")

            title = clean_html(raw_title)
            description = clean_html(raw_description)
            text = f"{title} {description}"

            matched_stocks = stock_master_service.find_by_name_in_text(
                text=text,
                min_name_length=min_stock_name_length,
                ignore_names=ignore_stock_names,
            )

            if not matched_stocks:
                continue

            matched_positive = contains_any(text, positive_keywords)
            matched_negative = contains_any(text, negative_keywords)

            for matched_stock in matched_stocks:
                data = candidates[matched_stock.code]

                data["name"] = matched_stock.name
                data["code"] = matched_stock.code
                data["market"] = matched_stock.market
                data["matched_theme_keywords"].add(keyword)

                for pk in matched_positive:
                    data["matched_positive_keywords"].add(pk)

                for nk in matched_negative:
                    data["matched_negative_keywords"].add(nk)

                if title not in data["news_titles"]:
                    data["news_titles"].append(title)

    if not candidates:
        print()
        print("감지된 후보 종목이 없습니다.")
        return

    candidate_list = []

    for code, data in candidates.items():
        news_count = len(data["news_titles"])
        theme_count = len(data["matched_theme_keywords"])
        positive_count = len(data["matched_positive_keywords"])
        negative_count = len(data["matched_negative_keywords"])

        score = 0
        score += news_count * 10
        score += theme_count * 5
        score += positive_count * 15
        score -= negative_count * 20

        data["score"] = score

        if score >= min_candidate_score:
            candidate_list.append(data)

    candidate_list.sort(key=lambda x: x["score"], reverse=True)

    print()
    print("감지된 후보 종목")
    print("=" * 70)

    for idx, candidate in enumerate(candidate_list[:20], start=1):
        theme_keywords = ", ".join(sorted(candidate["matched_theme_keywords"])) or "-"
        positive_events = ", ".join(sorted(candidate["matched_positive_keywords"])) or "-"
        negative_events = ", ".join(sorted(candidate["matched_negative_keywords"])) or "-"

        print(f"\n[{idx}] {candidate['name']}({candidate['code']}) / {candidate['market']}")
        print(f"후보 점수: {candidate['score']}")
        print(f"테마 키워드: {theme_keywords}")
        print(f"긍정 이벤트: {positive_events}")
        print(f"위험 이벤트: {negative_events}")
        print("관련 뉴스:")

        for title in candidate["news_titles"][:3]:
            print(f"- {title}")

    print()
    print("=" * 70)
    answer = input(
        "후보 중 관심종목에 등록할 종목코드를 입력하세요. 여러 개면 콤마로 구분, 건너뛰려면 엔터: "
    ).strip()

    if not answer:
        print("등록하지 않고 종료합니다.")
        return

    codes = [code.strip() for code in answer.split(",") if code.strip()]

    for code in codes:
        target = None

        for candidate in candidate_list:
            if candidate["code"] == code:
                target = candidate
                break

        if not target:
            print(f"후보 목록에 없는 종목코드입니다: {code}")
            continue

        stock_service.add_stock(
            code=target["code"],
            name=target["name"],
            market=target["market"],
            sector="AUTO_THEME_CANDIDATE",
        )

    print("후보 종목 관심등록 처리 완료")


if __name__ == "__main__":
    main()
