from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config.settings import settings


DATABASE_URL = settings.DATABASE_URL


def _build_connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}

    return {}


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """
    SQLite 파일 DB를 사용할 때 상위 폴더가 없으면 생성한다.

    지원 예:
    - sqlite:///data/stock_ai_trader.db
    - sqlite:////app/data/stock_ai_trader.db
    """
    if not database_url.startswith("sqlite"):
        return

    path_text = database_url.replace("sqlite:///", "", 1)

    if path_text.startswith("/"):
        db_path = Path(path_text)
    else:
        db_path = settings.BASE_DIR / path_text

    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    connect_args=_build_connect_args(DATABASE_URL),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Session:
    """
    기존 코드 호환용 DB 세션 생성 함수.

    기존 scripts/run_auto_pipeline.py가 get_db()를 사용하고 있으므로 유지한다.
    이 함수로 받은 세션은 호출한 쪽에서 close 하는 것이 가장 좋다.
    """
    return SessionLocal()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    신규 코드에서 권장하는 DB 세션 사용 방식.

    예:
        with db_session() as db:
            ...
    """
    db = SessionLocal()

    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
