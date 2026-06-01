import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.analysis.technical_indicator import (
    calculate_moving_average,
    calculate_recent_return,
    calculate_volume_ratio,
    score_price,
)
from app.database.connection import get_db
from app.database.models import DailyPrice
from app.services.stock_service import StockService


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

    stock_code = input("가격 점수를 계산할 종목코드 입력: ").strip()

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

    if not prices:
        print("저장된 주가 데이터가 없습니다.")
        print("먼저 python scripts/collect_prices.py 를 실행하세요.")
        return

    close_prices = [price.close_price for price in prices if price.close_price is not None]
    volumes = [price.volume for price in prices if price.volume is not None]

    if len(close_prices) < 21:
        print("가격 점수를 계산하려면 최소 21거래일 이상의 주가 데이터가 필요합니다.")
        print("python scripts/collect_prices.py 에서 60일 이상 수집해보세요.")
        return

    current_price = close_prices[-1]
    return_5d = calculate_recent_return(close_prices, 5)
    return_20d = calculate_recent_return(close_prices, 20)
    ma20 = calculate_moving_average(close_prices, 20)
    volume_ratio = calculate_volume_ratio(volumes, 20)

    result = score_price(
        return_5d=return_5d,
        return_20d=return_20d,
        current_price=current_price,
        ma20=ma20,
        volume_ratio=volume_ratio,
    )

    print()
    print(f"{target_stock.name}({target_stock.code}) 가격 분석")
    print("=" * 60)
    print(f"현재가: {current_price:,.0f}원")
    print(f"5일 수익률: {return_5d if return_5d is not None else '데이터 부족'}%")
    print(f"20일 수익률: {return_20d if return_20d is not None else '데이터 부족'}%")
    print(f"20일 이동평균: {ma20:,.0f}원" if ma20 is not None else "20일 이동평균: 데이터 부족")
    print(f"거래량 비율: {volume_ratio if volume_ratio is not None else '데이터 부족'}배")
    print("-" * 60)
    print(f"가격 점수: {result['score']}/100")

    print()
    print("[점수 근거]")
    if result["reasons"]:
        for reason in result["reasons"]:
            print(f"- {reason}")
    else:
        print("- 특별한 가격/거래량 신호가 없습니다.")


if __name__ == "__main__":
    main()
