import re
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.services.discord_service import DiscordService


def get_latest_final_comparison_file() -> Path | None:
    final_dir = ROOT_DIR / "reports" / "final_comparisons"

    if not final_dir.exists():
        return None

    files = list(final_dir.glob("*_final_comparison.txt"))

    if not files:
        return None

    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)

    return files[0]


def read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_section(text: str, section_number: int) -> str:
    """
    '10. 최종 참고 판단', '11. 실전 대응 기준' 같은 번호 섹션을 추출한다.
    마크다운 제목 형식과 일반 번호 형식을 둘 다 어느 정도 지원한다.
    """
    pattern = rf"(?:^|\n)(?:#+\s*)?{section_number}\.\s+.*?(?=\n(?:#+\s*)?{section_number + 1}\.\s+|\Z)"

    match = re.search(pattern, text, flags=re.DOTALL)

    if not match:
        return ""

    return match.group(0).strip()


def extract_risk_keywords(text: str) -> str:
    lines = []

    important_words = [
        "손절",
        "익절",
        "진입",
        "트레일링",
        "관망",
        "주의 필요",
        "최종 참고 판단",
        "실전 대응 기준",
    ]

    for line in text.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        if any(word in clean_line for word in important_words):
            lines.append(clean_line)

    return "\n".join(lines[:20])


def make_discord_summary(file_path: Path, report_text: str) -> str:
    modified_time = datetime.fromtimestamp(file_path.stat().st_mtime).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    final_judgment = extract_section(report_text, 10)
    trade_plan = extract_section(report_text, 11)

    if final_judgment or trade_plan:
        preview = f"""
{final_judgment}

{trade_plan}
""".strip()
    else:
        preview = extract_risk_keywords(report_text)

    if not preview:
        preview = report_text.strip()

    max_preview_length = 1400

    if len(preview) > max_preview_length:
        preview = preview[:max_preview_length].rstrip() + "\n..."

    message = f"""
📊 **주식 AI 최종 비교 리포트 생성 완료**

**파일명**
`{file_path.name}`

**생성/수정 시간**
`{modified_time}`

**핵심 판단 / 실전 대응 기준**
{preview}

📎 전체 리포트는 첨부 파일을 확인하세요.
""".strip()

    if len(message) > 1900:
        message = message[:1900].rstrip() + "\n..."

    return message


def main():
    latest_file = get_latest_final_comparison_file()

    if not latest_file:
        print("최종 비교 리포트 파일이 없습니다.")
        print("먼저 아래 명령어를 실행하세요.")
        print("python scripts/generate_final_comparison.py")
        return

    report_text = read_text(latest_file)
    message = make_discord_summary(latest_file, report_text)

    print("Discord 전송 대상 파일")
    print("=" * 70)
    print(latest_file)
    print("=" * 70)

    try:
        discord_service = DiscordService()
        discord_service.send_file_with_message(
            content=message,
            file_path=latest_file,
        )

        print("Discord 전송 완료")

    except Exception as e:
        print(f"Discord 전송 실패: {e}")


if __name__ == "__main__":
    main()
