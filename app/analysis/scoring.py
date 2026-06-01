POSITIVE_KEYWORDS = [
    "수주",
    "계약",
    "흑자전환",
    "실적개선",
    "실적 개선",
    "신사업",
    "공급",
    "투자",
    "협력",
    "인수",
    "매출 증가",
    "영업이익 증가",
    "최대 실적",
    "호실적",
    "성장",
    "확대",
    "상승",
    "강세",
]

NEGATIVE_KEYWORDS = [
    "적자",
    "실적 부진",
    "영업손실",
    "소송",
    "횡령",
    "배임",
    "유상증자",
    "전환사채",
    "CB",
    "감사의견",
    "상장폐지",
    "불성실공시",
    "하락",
    "약세",
    "급락",
    "리스크",
]


def score_news(news_titles: list[str]) -> dict:
    """
    뉴스 제목 리스트를 받아서 뉴스 점수를 계산한다.

    기본 점수는 50점.
    긍정 키워드가 있으면 +5점.
    부정 키워드가 있으면 -10점.
    최종 점수는 0~100 사이로 제한한다.
    """

    score = 50
    matched_positive = []
    matched_negative = []

    for title in news_titles:
        for keyword in POSITIVE_KEYWORDS:
            if keyword in title:
                score += 5
                matched_positive.append(
                    {
                        "title": title,
                        "keyword": keyword,
                    }
                )

        for keyword in NEGATIVE_KEYWORDS:
            if keyword in title:
                score -= 10
                matched_negative.append(
                    {
                        "title": title,
                        "keyword": keyword,
                    }
                )

    score = max(0, min(100, score))

    return {
        "score": score,
        "positive_matches": matched_positive,
        "negative_matches": matched_negative,
    }
