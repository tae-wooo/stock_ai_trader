import time

from openai import OpenAI

from app.config.settings import settings


class ComparisonReporter:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_comparison(self, comparison_prompt: str) -> str:
        max_retries = 3
        wait_seconds = 5
        last_error = None

        system_message = (
            "너는 신중한 투자 분석 검토자다. "
            "두 AI 리포트를 비교하되, 매수/매도를 단정하지 말고 "
            "공통점, 차이점, 리스크, 초보자가 참고할 핵심 판단을 정리한다. "
            "특히 사용자가 실제로 진입을 고민할 때 참고할 수 있도록 "
            "진입 기준, 손절 기준, 익절 기준, 트레일링 스탑 기준을 반드시 제시한다. "
            "다만 이것은 투자 추천이 아니라 리스크 관리 참고 기준임을 명확히 한다."
        )

        final_prompt = f"""
아래 비교 프롬프트를 바탕으로 최종 비교 리포트를 작성해라.

중요한 출력 규칙:
1. 반드시 1번부터 11번까지 모두 작성해라.
2. 문장이 중간에 끊기지 않게 완성해라.
3. 각 항목은 핵심 위주로 정리해라.
4. 매수/매도를 단정하지 말고 참고 의견으로만 말해라.
5. 초보자가 볼 수 있게 쉽게 설명해라.
6. 제공된 리포트에 현재가, 수익률, 이동평균선, 거래량, 종목 유형, 매매 기준 정보가 있으면 반드시 반영해라.
7. 현재가가 명시되어 있으면 손절가/익절가를 대략적인 가격 범위로도 계산해라.
8. 현재가가 없으면 가격 대신 퍼센트 기준으로 제시해라.
9. 단기 과열 종목이면 신규 진입보다 관망/눌림목 기준을 우선 제시해라.
10. 손절 기준은 반드시 포함해라.
11. 마지막에는 투자 책임과 리스크를 한 문장으로 경고해라.

아래 형식으로 작성해라.

1. 두 AI의 공통 의견
2. 두 AI의 차이점
3. OpenAI 리포트의 장점
4. Gemini 리포트의 장점
5. OpenAI 리포트의 아쉬운 점
6. Gemini 리포트의 아쉬운 점
7. 더 보수적인 판단을 한 쪽
8. 더 설득력 있는 판단을 한 쪽
9. 초보자가 최종적으로 참고해야 할 핵심 포인트
10. 최종 참고 판단
11. 실전 대응 기준
   - 현재 상태:
   - 신규 진입 기준:
   - 진입하면 안 되는 조건:
   - 1차 익절 기준:
   - 2차 익절 기준:
   - 손절 기준:
   - 트레일링 스탑 기준:
   - 보유 중일 때 대응:
   - 한 줄 결론:

중요:
- 손절 기준은 예: 진입가 대비 -4~6%, -6~10%, 20일선 이탈, 급등 시작 구간 이탈 같은 식으로 반드시 제시해라.
- 익절 기준은 예: +5~8%, +8~12%, +15~20%처럼 범위로 제시해라.
- 과열 종목이면 "지금 바로 진입"이 아니라 "눌림목 확인 후"라고 말해라.
- 확실하지 않은 경우에는 "데이터 부족"이라고 말하되, 그래도 참고 가능한 리스크 관리 범위는 제시해라.

[비교 프롬프트]
{comparison_prompt}
""".strip()

        for attempt in range(1, max_retries + 1):
            try:
                print(f"OpenAI 비교 리포트 호출 시도 {attempt}/{max_retries}")

                response = self.client.responses.create(
                    model="gpt-5.4-mini",
                    input=[
                        {
                            "role": "system",
                            "content": system_message,
                        },
                        {
                            "role": "user",
                            "content": final_prompt,
                        },
                    ],
                    max_output_tokens=4000,
                )

                if not response.output_text:
                    raise ValueError("OpenAI 비교 리포트 응답이 비어 있습니다.")

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
