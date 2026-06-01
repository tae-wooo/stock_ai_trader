import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.database.connection import get_db
from app.services.stock_master_service import StockMasterService


def main():
    db = get_db()
    service = StockMasterService(db)

    print("전체 상장 종목 목록 동기화 시작")
    saved_count = service.sync_stock_master()

    print(f"신규 저장된 종목 수: {saved_count}개")

    total_count = len(service.get_all())
    print(f"전체 저장된 종목 수: {total_count}개")


if __name__ == "__main__":
    main()
