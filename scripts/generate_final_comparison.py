import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.ai.comparison_reporter import ComparisonReporter


def get_comparison_prompt_files() -> list[Path]:
    comparison_dir = ROOT_DIR / "reports" / "comparisons"

    if not comparison_dir.exists():
        return []

    files = list(comparison_dir.glob("*_comparison_prompt.txt"))
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)

    return files


def select_comparison_prompt_file(files: list[Path]) -> Path | None:
    if not files:
        print("비교 프롬프트 파일이 없습니다.")
        print("먼저 python scripts/run_auto_pipeline.py 를 실행하세요.")
        return None

    print("최근 비교 프롬프트 목록")
    print("=" * 70)

    for index, path in enumerate(files[:10], start=1):
        modified_time = datetime.fromtimestamp(path.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        print(f"{index}. {path.name} / 수정시간: {modified_time}")

    print("=" * 70)

    answer = input("최종 비교 리포트를 만들 번호 입력, 최신 파일은 엔터: ").strip()

    if not answer:
        return files[0]

    try:
        selected_index = int(answer)
    except ValueError:
        print("숫자를 입력해야 합니다.")
        return None

    if selected_index < 1 or selected_index > min(len(files), 10):
        print("잘못된 번호입니다.")
        return None

    return files[selected_index - 1]


def read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_final_comparison(source_path: Path, content: str) -> Path:
    output_dir = ROOT_DIR / "reports" / "final_comparisons"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = source_path.name.replace(
        "_comparison_prompt.txt",
        "_final_comparison.txt",
    )

    output_path = output_dir / output_filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


def main():
    files = get_comparison_prompt_files()
    selected_file = select_comparison_prompt_file(files)

    if not selected_file:
        return

    comparison_prompt = read_text(selected_file)

    print()
    print("최종 비교 리포트 생성 중...")
    print("=" * 70)
    print(f"선택 파일: {selected_file}")

    try:
        reporter = ComparisonReporter()
        final_comparison = reporter.generate_comparison(comparison_prompt)

        output_path = save_final_comparison(
            source_path=selected_file,
            content=final_comparison,
        )

        print()
        print(final_comparison)

        print()
        print("최종 비교 리포트 저장 완료")
        print("=" * 70)
        print(f"파일 위치: {output_path}")

    except Exception as e:
        print(f"최종 비교 리포트 생성 실패: {e}")


if __name__ == "__main__":
    main()
