from app.database.models import Stock


class StockService:
    def __init__(self, db):
        self.db = db

    def add_stock(
        self,
        code: str,
        name: str,
        market: str | None = None,
        sector: str | None = None,
    ):
        exists = self.db.query(Stock).filter(Stock.code == code).first()

        if exists:
            print(f"이미 등록된 종목입니다: {exists.name}({exists.code})")
            return exists

        stock = Stock(
            code=code,
            name=name,
            market=market,
            sector=sector,
        )

        self.db.add(stock)
        self.db.commit()
        self.db.refresh(stock)

        print(f"종목 등록 완료: {stock.name}({stock.code})")
        return stock

    def get_all_stocks(self):
        return self.db.query(Stock).order_by(Stock.id.asc()).all()

    def delete_stock(self, code: str) -> bool:
        stock = self.db.query(Stock).filter(Stock.code == code).first()

        if not stock:
            return False

        self.db.delete(stock)
        self.db.commit()

        return True
