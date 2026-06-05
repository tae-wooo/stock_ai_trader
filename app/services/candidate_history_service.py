import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.database.models import AiAnalysisRun, CandidateSnapshot


class CandidateHistoryService:
    """
    후보 감지 이력과 AI 분석 실행 이력을 저장하는 서비스.

    기존 CandidateStockService:
        - 현재 후보 상태 관리

    CandidateHistoryService:
        - 후보가 감지된 시점의 판단 근거 저장
        - AI 분석 실행/성공/실패 이력 저장
    """

    def __init__(self, db):
        self.db = db

    def _to_json_text(self, value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    def _append_error(self, old_error: str | None, new_error: str) -> str:
        if not old_error:
            return new_error

        return f"{old_error}\n{new_error}"

    def create_candidate_snapshot(
        self,
        *,
        stock_code: str,
        stock_name: str,
        market: str | None,
        status: str,
        score: int,
        current_price: float | None,
        price_allowed: bool | None,
        price_reason: str | None,
        detected_keywords: list[str],
        positive_keywords: list[str],
        negative_keywords: list[str],
        news_titles: list[str],
        reason: dict | None = None,
    ) -> CandidateSnapshot:
        snapshot = CandidateSnapshot(
            stock_code=stock_code,
            stock_name=stock_name,
            market=market,
            detected_date=date.today(),
            detected_at=datetime.utcnow(),
            status=status,
            score=score,
            current_price=current_price,
            price_allowed=price_allowed,
            price_reason=price_reason,
            detected_keywords=self._to_json_text(detected_keywords),
            positive_keywords=self._to_json_text(positive_keywords),
            negative_keywords=self._to_json_text(negative_keywords),
            news_titles=self._to_json_text(news_titles[:20]),
            news_count=len(news_titles),
            theme_keyword_count=len(detected_keywords),
            positive_keyword_count=len(positive_keywords),
            negative_keyword_count=len(negative_keywords),
            reason_json=self._to_json_text(reason or {}),
        )

        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)

        return snapshot

    def start_ai_analysis_run(
        self,
        *,
        stock_code: str,
        stock_name: str,
    ) -> AiAnalysisRun:
        run = AiAnalysisRun(
            stock_code=stock_code,
            stock_name=stock_name,
            run_date=date.today(),
            started_at=datetime.utcnow(),
            status="STARTED",
        )

        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        return run

    def mark_ai_analysis_scored(
        self,
        *,
        run: AiAnalysisRun,
        result: dict,
    ) -> AiAnalysisRun:
        run.current_price = result.get("current_price")
        run.return_5d = result.get("return_5d")
        run.return_20d = result.get("return_20d")
        run.ma20 = result.get("ma20")
        run.volume_ratio = result.get("volume_ratio")

        run.price_score = result.get("price_score")
        run.news_score = result.get("news_score")
        run.disclosure_score = result.get("disclosure_score")
        run.total_score = result.get("total_score")
        run.judgment = result.get("judgment")

        run.status = "SCORED"
        run.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)

        return run

    def mark_prompt_saved(
        self,
        *,
        run: AiAnalysisRun,
        prompt_path: Path,
    ) -> AiAnalysisRun:
        run.prompt_path = str(prompt_path)
        run.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)

        return run

    def mark_openai_result(
        self,
        *,
        run: AiAnalysisRun,
        success: bool,
        report_path: Path | None = None,
        error_message: str | None = None,
    ) -> AiAnalysisRun:
        run.openai_success = success

        if report_path is not None:
            run.openai_report_path = str(report_path)

        if error_message:
            run.error_message = self._append_error(
                run.error_message,
                f"OpenAI: {error_message}",
            )

        run.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)

        return run

    def mark_gemini_result(
        self,
        *,
        run: AiAnalysisRun,
        success: bool,
        report_path: Path | None = None,
        error_message: str | None = None,
    ) -> AiAnalysisRun:
        run.gemini_success = success

        if report_path is not None:
            run.gemini_report_path = str(report_path)

        if error_message:
            run.error_message = self._append_error(
                run.error_message,
                f"Gemini: {error_message}",
            )

        run.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)

        return run

    def mark_comparison_prompt_saved(
        self,
        *,
        run: AiAnalysisRun,
        comparison_prompt_path: Path,
    ) -> AiAnalysisRun:
        run.comparison_prompt_path = str(comparison_prompt_path)
        run.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)

        return run

    def mark_final_report_result(
        self,
        *,
        run: AiAnalysisRun,
        success: bool,
        final_report_path: Path | None = None,
        error_message: str | None = None,
    ) -> AiAnalysisRun:
        run.comparison_success = success

        if final_report_path is not None:
            run.final_report_path = str(final_report_path)

        if error_message:
            run.error_message = self._append_error(
                run.error_message,
                f"Comparison: {error_message}",
            )

        run.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)

        return run

    def mark_discord_result(
        self,
        *,
        run: AiAnalysisRun,
        success: bool,
        error_message: str | None = None,
    ) -> AiAnalysisRun:
        run.discord_success = success

        if error_message:
            run.error_message = self._append_error(
                run.error_message,
                f"Discord: {error_message}",
            )

        run.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(run)

        return run

    def finish_ai_analysis_run(
        self,
        *,
        run: AiAnalysisRun,
        status: str,
        error_message: str | None = None,
    ) -> AiAnalysisRun:
        run.status = status
        run.finished_at = datetime.utcnow()
        run.updated_at = datetime.utcnow()

        if error_message:
            run.error_message = self._append_error(
                run.error_message,
                error_message,
            )

        self.db.commit()
        self.db.refresh(run)

        return run
