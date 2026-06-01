import time

from google import genai

from app.config.settings import settings


class GeminiReporter:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY가 .env에 설정되어 있지 않습니다.")

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generate_report(self, prompt: str) -> str:
        system_instruction = (
            "너는 신중한 주식 분석 보조 AI다. "
            "과장하지 말고 제공된 데이터만 근거로 분석한다. "
            "투자 조언은 참고용이며 리스크를 반드시 언급한다."
        )

        full_prompt = f"{system_instruction}\n\n{prompt}"

        max_retries = 3
        wait_seconds = 10

        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                print(f"Gemini 호출 시도 {attempt}/{max_retries}")

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_prompt,
                )

                if not response.text:
                    raise ValueError("Gemini 응답이 비어 있습니다.")

                return response.text

            except Exception as e:
                last_error = e
                error_message = str(e)

                retryable_errors = [
                    "503",
                    "UNAVAILABLE",
                    "high demand",
                    "temporarily",
                    "timeout",
                    "429",
                    "RESOURCE_EXHAUSTED",
                ]

                can_retry = any(keyword in error_message for keyword in retryable_errors)

                if attempt < max_retries and can_retry:
                    print(f"Gemini 일시적 오류 발생. {wait_seconds}초 후 재시도합니다.")
                    print(f"오류 내용: {error_message}")
                    time.sleep(wait_seconds)
                    wait_seconds *= 2
                    continue

                raise last_error

        raise last_error
