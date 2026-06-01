import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


def run_command(command: list[str]):
    print()
    print(f"실행 명령어: {' '.join(command)}")
    print("=" * 70)

    result = subprocess.run(
        command,
        cwd=ROOT_DIR,
    )

    if result.returncode != 0:
        raise RuntimeError(f"명령어 실행 실패: {' '.join(command)}")


def get_stock_master_count() -> int:
    from app.database.connection import get_db
    from app.services.stock_master_service import StockMasterService

    db = get_db()

    try:
        stock_master_service = StockMasterService(db)
        return len(stock_master_service.get_all())
    finally:
        db.close()


def main():
    print()
    print("Docker 자동 실행 시작")
    print("=" * 70)

    run_command([sys.executable, "scripts/init_db.py"])

    try:
        stock_master_count = get_stock_master_count()

        print()
        print("종목 마스터 상태 확인")
        print("=" * 70)
        print(f"현재 저장된 종목 수: {stock_master_count}개")

        if stock_master_count == 0:
            print("종목 마스터가 비어 있어 동기화를 실행합니다.")
            run_command([sys.executable, "scripts/sync_stock_master.py"])
        else:
            print("종목 마스터가 이미 존재하여 동기화를 건너뜁니다.")

    except Exception as e:
        print(f"종목 마스터 확인 중 오류 발생: {e}")
        print("안전하게 sync_stock_master.py를 실행합니다.")
        run_command([sys.executable, "scripts/sync_stock_master.py"])

    run_command([sys.executable, "scripts/run_auto_pipeline.py"])

    print()
    print("Docker 자동 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()
