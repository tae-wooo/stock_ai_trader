POSITIVE_DISCLOSURE_KEYWORDS = {
    "단일판매ㆍ공급계약체결": "공급계약 체결은 매출 증가 기대 요인이 될 수 있음",
    "공급계약": "공급계약 체결은 매출 증가 기대 요인이 될 수 있음",
    "자기주식취득": "자사주 취득은 주가 방어 또는 주주환원 신호일 수 있음",
    "자사주": "자사주 관련 공시는 주주환원 신호일 수 있음",
    "현금ㆍ현물배당": "배당 공시는 주주환원 측면에서 긍정적일 수 있음",
    "배당": "배당 공시는 주주환원 측면에서 긍정적일 수 있음",
    "영업실적": "실적 발표 공시는 기업 상태를 판단하는 핵심 자료임",
}


NEGATIVE_DISCLOSURE_KEYWORDS = {
    "유상증자": "주식 수 증가로 기존 주주 지분가치가 희석될 수 있음",
    "전환사채": "향후 주식으로 전환될 수 있는 물량 부담이 생길 수 있음",
    "CB": "전환사채 관련 이슈일 수 있어 물량 부담을 확인해야 함",
    "신주인수권부사채": "향후 신주 발행 가능성이 있어 희석 리스크가 있음",
    "BW": "신주인수권부사채 관련 이슈일 수 있어 희석 리스크를 확인해야 함",
    "최대주주 변경": "경영권 변화 또는 지배구조 불확실성이 생길 수 있음",
    "소송": "법적 분쟁으로 비용 또는 평판 리스크가 발생할 수 있음",
    "횡령": "기업 신뢰도에 큰 악영향을 줄 수 있음",
    "배임": "경영진 신뢰도와 기업 가치에 큰 악영향을 줄 수 있음",
    "감사의견": "회계 신뢰성과 상장 유지 리스크를 확인해야 함",
    "상장폐지": "거래정지 또는 상장폐지 위험이 있을 수 있음",
    "불성실공시": "공시 신뢰도 저하 및 제재 가능성이 있음",
    "거래정지": "매매가 제한될 수 있는 큰 리스크임",
    "관리종목": "상장 유지와 재무 안정성 측면에서 주의가 필요함",
}


def score_disclosures(disclosure_titles: list[str]) -> dict:
    """
    공시 제목 리스트를 받아 공시 점수를 계산한다.

    기본 점수는 50점.
    긍정 공시 키워드가 있으면 +10점.
    부정/위험 공시 키워드가 있으면 -15점.
    최종 점수는 0~100 사이로 제한한다.
    """

    score = 50
    positive_matches = []
    negative_matches = []

    for title in disclosure_titles:
        for keyword, reason in POSITIVE_DISCLOSURE_KEYWORDS.items():
            if keyword in title:
                score += 10
                positive_matches.append(
                    {
                        "title": title,
                        "keyword": keyword,
                        "reason": reason,
                    }
                )

        for keyword, reason in NEGATIVE_DISCLOSURE_KEYWORDS.items():
            if keyword in title:
                score -= 15
                negative_matches.append(
                    {
                        "title": title,
                        "keyword": keyword,
                        "reason": reason,
                    }
                )

    score = max(0, min(100, score))

    return {
        "score": score,
        "positive_matches": positive_matches,
        "negative_matches": negative_matches,
    }
