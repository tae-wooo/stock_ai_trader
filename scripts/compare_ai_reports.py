from openai import OpenAI

from app.config.settings import settings


class ComparisonReporter:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_comparison(self, comparison_prompt: str) -> str:
        response = self.client.responses.create(
            model="gpt-5.5-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "너는 신중한 투자 분석 검토자다. "
                        "두 AI 리포트를 비교하되, 매수/매도를 단정하지 말고 "
                        "공통점, 차이점, 리스크, 초보자가 참고할 핵심 판단을 정리한다."
                    ),
                },
                {
                    "role": "user",
                    "content": comparison_prompt,
                },
            ],
            max_output_tokens=1500,
        )

        return response.output_text
