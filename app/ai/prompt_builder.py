def build_stock_analysis_prompt(
    stock_name: str,
    stock_code: str,
    current_price,
    return_5d,
    return_20d,
    ma20,
    volume_ratio,
    price_score: int,
    news_score: int,
    disclosure_score: int,
    total_score: int,
    judgment: str,
    news_titles: list[str],
    disclosure_titles: list[str],
    price_reasons: list[str],
    news_positive_matches: list[dict],
    news_negative_matches: list[dict],
    disclosure_positive_matches: list[dict],
    disclosure_negative_matches: list[dict],
) -> str:
    def value_or_unknown(value, suffix=""):
        if value is None:
            return "데이터 부족"
        return f"{value}{suffix}"

    def list_to_bullets(items: list[str], empty_message: str = "없음") -> str:
        if not items:
            return f"- {empty_message}"
        return "\n".join([f"- {item}" for item in items])

    def matches_to_bullets(matches: list[dict], empty_message: str = "없음") -> str:
        if not matches:
            return f"- {empty_message}"

        lines = []
        for item in matches[:5]:
            keyword = item.get("keyword", "-")
            title = item.get("title", "-")
            reason = item.get("reason")

            if reason:
                lines.append(f"- 키워드: {keyword} / 제목: {title} / 해석: {reason}")
            else:
                lines.append(f"- 키워드: {keyword} / 제목: {title}")

        return "\n".join(lines)

    price_reason_text = list_to_bullets(price_reasons, "특별한 가격 신호 없음")
    news_text = list_to_bullets(news_titles[:10], "뉴스 데이터 없음")
    disclosure_text = list_to_bullets(disclosure_titles[:10], "공시 데이터 없음")

    news_positive_text = matches_to_bullets(news_positive_matches)
    news_negative_text = matches_to_bullets(news_negative_matches)
    disclosure_positive_text = matches_to_bullets(disclosure_positive_matches)
    disclosure_negative_text = matches_to_bullets(disclosure_negative_matches)

    prompt = f"""
너는 신중한 주식 분석 보조 AI다.

반드시 지켜야 할 규칙:
1. 아래 제공된 데이터만 근거로 분석해라.
2. 모르는 내용은 추측하지 말고 "데이터 부족"이라고 말해라.
3. 절대 무조건 매수를 추천하지 마라.
4. 초보자도 이해할 수 있게 쉽게 설명해라.
5. 투자 의견은 참고용이며, 리스크를 반드시 같이 설명해라.
6. 단기 관점과 중장기 관점을 나눠서 설명해라.
7. 점수가 높아도 위험 요소가 있으면 반드시 언급해라.

[종목 정보]
- 종목명: {stock_name}
- 종목코드: {stock_code}

[가격 지표]
- 현재가: {value_or_unknown(current_price, "원")}
- 5일 수익률: {value_or_unknown(return_5d, "%")}
- 20일 수익률: {value_or_unknown(return_20d, "%")}
- 20일 이동평균: {value_or_unknown(ma20, "원")}
- 거래량 비율: {value_or_unknown(volume_ratio, "배")}

[가격 점수 근거]
{price_reason_text}

[최근 뉴스 제목]
{news_text}

[최근 공시 제목]
{disclosure_text}

[뉴스 키워드 분석]
긍정 키워드:
{news_positive_text}

부정 키워드:
{news_negative_text}

[공시 키워드 분석]
긍정 공시 키워드:
{disclosure_positive_text}

위험 공시 키워드:
{disclosure_negative_text}

[점수]
- 가격 점수: {price_score}/100
- 뉴스 점수: {news_score}/100
- 공시 점수: {disclosure_score}/100
- 종합 점수: {total_score}/100
- 프로그램 판단: {judgment}

[점수 판단 기준]
- 80점 이상: 강한 관심 후보
- 65점 이상: 관심 후보
- 50점 이상: 중립 / 관망
- 35점 이상: 주의 필요
- 35점 미만: 위험

아래 형식으로 분석 리포트를 작성해라.

1. 한 줄 요약
2. 현재 종목 상태
3. 긍정 요인
4. 위험 요인
5. 단기 관점
6. 중장기 관점
7. 초보자가 조심해야 할 점
8. 최종 판단: 강한 관심 후보 / 관심 후보 / 중립 / 주의 필요 / 위험 / 데이터 부족 중 하나
9. 확신도: 낮음 / 보통 / 높음
""".strip()

    return prompt
