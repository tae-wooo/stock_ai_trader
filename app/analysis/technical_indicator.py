def calculate_recent_return(prices: list[float], days: int) -> float | None:
    """
    최근 수익률을 계산한다.

    예:
    days=5면 현재 종가와 5거래일 전 종가를 비교한다.
    """

    if len(prices) <= days:
        return None

    current_price = prices[-1]
    past_price = prices[-days - 1]

    if past_price == 0:
        return None

    return round(((current_price - past_price) / past_price) * 100, 2)


def calculate_moving_average(prices: list[float], window: int) -> float | None:
    """
    이동평균선을 계산한다.

    예:
    window=20이면 최근 20개 종가의 평균을 계산한다.
    """

    if len(prices) < window:
        return None

    recent_prices = prices[-window:]
    return round(sum(recent_prices) / window, 2)


def calculate_volume_ratio(volumes: list[int], window: int = 20) -> float | None:
    """
    오늘 거래량이 최근 평균 거래량 대비 몇 배인지 계산한다.

    예:
    결과가 2.5면 최근 20일 평균 거래량보다 오늘 거래량이 2.5배 많다는 뜻.
    """

    if len(volumes) < window + 1:
        return None

    today_volume = volumes[-1]
    previous_volumes = volumes[-window - 1:-1]

    avg_volume = sum(previous_volumes) / window

    if avg_volume == 0:
        return None

    return round(today_volume / avg_volume, 2)


def score_price(
    return_5d: float | None,
    return_20d: float | None,
    current_price: float | None,
    ma20: float | None,
    volume_ratio: float | None,
) -> dict:
    """
    가격/거래량 기반 점수를 계산한다.

    기본 점수 50점.
    추세가 좋으면 +
    너무 급등했으면 일부 -
    거래량이 증가하면 +
    거래량이 과도하게 터지면 추격 위험으로 일부 -
    """

    score = 50
    reasons = []

    if return_5d is not None:
        if return_5d > 0:
            score += 10
            reasons.append(f"최근 5일 수익률이 양수입니다. ({return_5d}%)")
        if return_5d > 15:
            score -= 10
            reasons.append(f"최근 5일 상승률이 너무 큽니다. 단기 과열 가능성이 있습니다. ({return_5d}%)")
        if return_5d < -10:
            score -= 10
            reasons.append(f"최근 5일 하락폭이 큽니다. ({return_5d}%)")

    if return_20d is not None:
        if return_20d > 0:
            score += 10
            reasons.append(f"최근 20일 수익률이 양수입니다. ({return_20d}%)")
        if return_20d > 30:
            score -= 10
            reasons.append(f"최근 20일 상승률이 매우 큽니다. 추격매수 위험이 있습니다. ({return_20d}%)")
        if return_20d < -20:
            score -= 10
            reasons.append(f"최근 20일 하락폭이 큽니다. ({return_20d}%)")

    if current_price is not None and ma20 is not None:
        if current_price > ma20:
            score += 10
            reasons.append(f"현재가가 20일 이동평균선 위에 있습니다. 현재가={current_price}, MA20={ma20}")
        else:
            score -= 5
            reasons.append(f"현재가가 20일 이동평균선 아래에 있습니다. 현재가={current_price}, MA20={ma20}")

    if volume_ratio is not None:
        if volume_ratio >= 2:
            score += 15
            reasons.append(f"거래량이 최근 평균 대비 증가했습니다. ({volume_ratio}배)")
        if volume_ratio >= 5:
            score -= 10
            reasons.append(f"거래량이 과도하게 급증했습니다. 단기 변동성 위험이 있습니다. ({volume_ratio}배)")

    score = max(0, min(100, score))

    return {
        "score": score,
        "reasons": reasons,
    }
