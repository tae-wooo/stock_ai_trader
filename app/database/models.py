from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
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
        UniqueConstraint(
            "stock_code",
            "trade_date",
            name="uq_daily_price_stock_date",
        ),
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


class StockMaster(Base):
    __tablename__ = "stock_master"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    market = Column(String(30), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class CandidateStock(Base):
    __tablename__ = "candidate_stocks"

    id = Column(Integer, primary_key=True, index=True)

    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100), nullable=False)
    market = Column(String(30), nullable=True)

    detected_keywords = Column(Text, nullable=True)
    positive_keywords = Column(Text, nullable=True)
    negative_keywords = Column(Text, nullable=True)
    news_titles = Column(Text, nullable=True)

    news_count = Column(Integer, default=0)
    theme_keyword_count = Column(Integer, default=0)
    positive_keyword_count = Column(Integer, default=0)
    negative_keyword_count = Column(Integer, default=0)

    score = Column(Integer, default=0)
    status = Column(String(30), default="CANDIDATE")

    first_detected_at = Column(DateTime, default=datetime.utcnow)
    last_detected_at = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("stock_code", name="uq_candidate_stock_code"),
    )


class CandidateSnapshot(Base):
    """
    후보 감지 당시의 이력 저장 테이블.

    CandidateStock은 종목별 현재 상태를 보관하고,
    CandidateSnapshot은 매 실행 시점의 판단 근거를 남긴다.
    """

    __tablename__ = "candidate_snapshots"

    id = Column(Integer, primary_key=True, index=True)

    stock_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(100), nullable=False)
    market = Column(String(30), nullable=True)

    detected_date = Column(Date, nullable=False, index=True)
    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    status = Column(String(30), nullable=False, default="CANDIDATE")
    score = Column(Integer, nullable=False, default=0)

    current_price = Column(Float, nullable=True)
    price_allowed = Column(Boolean, nullable=True)
    price_reason = Column(Text, nullable=True)

    detected_keywords = Column(Text, nullable=True)
    positive_keywords = Column(Text, nullable=True)
    negative_keywords = Column(Text, nullable=True)
    news_titles = Column(Text, nullable=True)

    news_count = Column(Integer, default=0)
    theme_keyword_count = Column(Integer, default=0)
    positive_keyword_count = Column(Integer, default=0)
    negative_keyword_count = Column(Integer, default=0)

    reason_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class AiAnalysisRun(Base):
    """
    AI 분석 1회 실행 단위 저장 테이블.

    reports/ 폴더에 저장되는 파일 경로와 성공/실패 상태를 DB에도 남긴다.
    """

    __tablename__ = "ai_analysis_runs"

    id = Column(Integer, primary_key=True, index=True)

    stock_code = Column(String(20), nullable=False, index=True)
    stock_name = Column(String(100), nullable=False)

    run_date = Column(Date, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    status = Column(String(30), nullable=False, default="STARTED")
    error_message = Column(Text, nullable=True)

    current_price = Column(Float, nullable=True)
    return_5d = Column(Float, nullable=True)
    return_20d = Column(Float, nullable=True)
    ma20 = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)

    price_score = Column(Integer, nullable=True)
    news_score = Column(Integer, nullable=True)
    disclosure_score = Column(Integer, nullable=True)
    total_score = Column(Integer, nullable=True)
    judgment = Column(String(50), nullable=True)

    prompt_path = Column(Text, nullable=True)
    openai_report_path = Column(Text, nullable=True)
    gemini_report_path = Column(Text, nullable=True)
    comparison_prompt_path = Column(Text, nullable=True)
    final_report_path = Column(Text, nullable=True)

    openai_success = Column(Boolean, default=False)
    gemini_success = Column(Boolean, default=False)
    comparison_success = Column(Boolean, default=False)
    discord_success = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class SignalPerformance(Base):
    """
    AI 분석 이후 성과 추적 테이블.

    추후 별도 스크립트에서 D+1, D+3, D+5, D+10, D+20 수익률을 채운다.
    """

    __tablename__ = "signal_performances"

    id = Column(Integer, primary_key=True, index=True)

    ai_analysis_run_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String(20), nullable=False, index=True)
    signal_date = Column(Date, nullable=False, index=True)
    signal_price = Column(Float, nullable=True)

    d1_return = Column(Float, nullable=True)
    d3_return = Column(Float, nullable=True)
    d5_return = Column(Float, nullable=True)
    d10_return = Column(Float, nullable=True)
    d20_return = Column(Float, nullable=True)

    max_return_20d = Column(Float, nullable=True)
    min_return_20d = Column(Float, nullable=True)

    hit_stop_loss = Column(Boolean, nullable=True)
    hit_take_profit_1 = Column(Boolean, nullable=True)
    hit_take_profit_2 = Column(Boolean, nullable=True)
    first_hit_event = Column(String(50), nullable=True)

    evaluated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "ai_analysis_run_id",
            name="uq_signal_performance_ai_analysis_run_id",
        ),
    )
