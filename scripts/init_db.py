import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import engine
from app.database.models import Base


def init_db():
    Base.metadata.create_all(bind=engine)
    print("DB 테이블 생성 완료")


if __name__ == "__main__":
    init_db()
