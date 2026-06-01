import time

from openai import OpenAI

from app.config.settings import settings


class OpenAiReporter:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_report(self, prompt: str) -> str:
        max_retries = 3
        wait_seconds = 5
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                print(f"OpenAI 호출 시도 {attempt}/{max_retries}")

                response = self.client.responses.create(
                    model="gpt-5.4-mini",
                    input=[
                        {
                            "role": "system",
                            "content": (
                                "너는 신중한 주식 분석 보조 AI다. "
                                "과장하지 말고 제공된 데이터만 근거로 분석한다. "
                                "투자 조언은 참고용이며 리스크를 반드시 언급한다."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    max_output_tokens=1500,
                )

                if not response.output_text:
                    raise ValueError("OpenAI 응답이 비어 있습니다.")

                return response.output_text

            except Exception as e:
                last_error = e
                error_message = str(e)

                retryable_errors = [
                    "429",
                    "rate_limit",
                    "timeout",
                    "temporarily",
                    "503",
                    "server_error",
                ]

                can_retry = any(keyword in error_message for keyword in retryable_errors)

                if attempt < max_retries and can_retry:
                    print(f"OpenAI 일시적 오류 발생. {wait_seconds}초 후 재시도합니다.")
                    print(f"오류 내용: {error_message}")
                    time.sleep(wait_seconds)
                    wait_seconds *= 2
                    continue

                raise last_error

        raise last_error
