from datetime import datetime, timedelta

from pykrx import stock

from app.database.models import DailyPrice


class PriceService:
    def __init__(self, db):
        self.db = db

    def collect_and_save(
        self,
        stock_code: str,
        days: int = 60,
    ):
        end_date = datetime.today()
        start_date = end_date - timedelta(days=days)

        start = start_date.strftime("%Y%m%d")
        end = end_date.strftime("%Y%m%d")

        df = stock.get_market_ohlcv_by_date(
            fromdate=start,
            todate=end,
            ticker=stock_code,
        )

        if df.empty:
            print("조회된 주가 데이터가 없습니다.")
            return 0

        saved_count = 0
        updated_count = 0

        for trade_date, row in df.iterrows():
            trade_date_value = trade_date.date()

            exists = (
                self.db.query(DailyPrice)
                .filter(
                    DailyPrice.stock_code == stock_code,
                    DailyPrice.trade_date == trade_date_value,
                )
                .first()
            )

            open_price = float(row["시가"])
            high_price = float(row["고가"])
            low_price = float(row["저가"])
            close_price = float(row["종가"])
            volume = int(row["거래량"])

            trading_value = None
            if "거래대금" in row:
                trading_value = int(row["거래대금"])

            change_rate = None
            if "등락률" in row:
                change_rate = float(row["등락률"])

            if exists:
                exists.open_price = open_price
                exists.high_price = high_price
                exists.low_price = low_price
                exists.close_price = close_price
                exists.volume = volume
                exists.trading_value = trading_value
                exists.change_rate = change_rate
                updated_count += 1
                continue

            daily_price = DailyPrice(
                stock_code=stock_code,
                trade_date=trade_date_value,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                trading_value=trading_value,
                change_rate=change_rate,
            )

            self.db.add(daily_price)
            saved_count += 1

        self.db.commit()

        print(f"신규 저장: {saved_count}개")
        print(f"기존 업데이트: {updated_count}개")

        return saved_count
