from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database.connection import Base


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    market = Column(String(30), nullable=True)
    sector = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False)
    trade_date = Column(Date, nullable=False)

    open_price = Column(Float, nullable=True)
    high_price = Column(Float, nullable=True)
    low_price = Column(Float, nullable=True)
    close_price = Column(Float, nullable=True)

    volume = Column(BigInteger, nullable=True)
    trading_value = Column(BigInteger, nullable=True)
    change_rate = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", name="uq_daily_price_stock_date"),
    )


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=True)

    title = Column(Text, nullable=False)
    link = Column(Text, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    published_at = Column(DateTime, nullable=True)

    sentiment = Column(String(30), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class Disclosure(Base):
    __tablename__ = "disclosures"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=True)

    report_no = Column(String(50), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    report_type = Column(String(100), nullable=True)
    dart_url = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)

    summary = Column(Text, nullable=True)
    risk_level = Column(String(30), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class AiReport(Base):
    __tablename__ = "ai_reports"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(20), nullable=False)
    report_date = Column(Date, nullable=False)

    report_text = Column(Text, nullable=False)
    total_score = Column(Integer, nullable=True)
    opinion = Column(String(30), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
