import json
from datetime import datetime, timedelta

from app.database.models import CandidateStock


class CandidateStockService:
    def __init__(self, db):
        self.db = db

    def _to_json_text(self, value) -> str:
        return json.dumps(value, ensure_ascii=False)

    def _from_json_text(self, value: str | None):
        if not value:
            return []

        try:
            return json.loads(value)
        except Exception:
            return []

    def upsert_candidate(
        self,
        stock_code: str,
        stock_name: str,
        market: str | None,
        detected_keywords: list[str],
        positive_keywords: list[str],
        negative_keywords: list[str],
        news_titles: list[str],
        score: int,
    ) -> CandidateStock:
        now = datetime.utcnow()

        candidate = (
            self.db.query(CandidateStock)
            .filter(CandidateStock.stock_code == stock_code)
            .first()
        )

        if candidate:
            old_detected = set(self._from_json_text(candidate.detected_keywords))
            old_positive = set(self._from_json_text(candidate.positive_keywords))
            old_negative = set(self._from_json_text(candidate.negative_keywords))
            old_titles = set(self._from_json_text(candidate.news_titles))

            merged_detected = sorted(old_detected.union(detected_keywords))
            merged_positive = sorted(old_positive.union(positive_keywords))
            merged_negative = sorted(old_negative.union(negative_keywords))
            merged_titles = sorted(old_titles.union(news_titles))

            old_score = candidate.score or 0

            candidate.stock_name = stock_name
            candidate.market = market
            candidate.detected_keywords = self._to_json_text(merged_detected)
            candidate.positive_keywords = self._to_json_text(merged_positive)
            candidate.negative_keywords = self._to_json_text(merged_negative)
            candidate.news_titles = self._to_json_text(merged_titles[:20])
            candidate.news_count = len(merged_titles)
            candidate.theme_keyword_count = len(merged_detected)
            candidate.positive_keyword_count = len(merged_positive)
            candidate.negative_keyword_count = len(merged_negative)
            candidate.score = max(old_score, score)
            candidate.last_detected_at = now
            candidate.updated_at = now

            if merged_negative:
                candidate.status = "RISK_BLOCKED"

            elif candidate.status == "AI_ANALYZED":
                if score >= old_score + 30:
                    candidate.status = "AUTO_REGISTERED"

            elif candidate.status == "PRICE_FILTERED":
                # 가격 조건을 다시 통과한 경우에는 CANDIDATE로 복구할 수 있게 한다.
                candidate.status = "CANDIDATE"

            elif candidate.status != "AUTO_REGISTERED":
                candidate.status = "CANDIDATE"

            self.db.commit()
            self.db.refresh(candidate)

            return candidate

        candidate = CandidateStock(
            stock_code=stock_code,
            stock_name=stock_name,
            market=market,
            detected_keywords=self._to_json_text(sorted(set(detected_keywords))),
            positive_keywords=self._to_json_text(sorted(set(positive_keywords))),
            negative_keywords=self._to_json_text(sorted(set(negative_keywords))),
            news_titles=self._to_json_text(news_titles[:20]),
            news_count=len(news_titles),
            theme_keyword_count=len(set(detected_keywords)),
            positive_keyword_count=len(set(positive_keywords)),
            negative_keyword_count=len(set(negative_keywords)),
            score=score,
            status="RISK_BLOCKED" if negative_keywords else "CANDIDATE",
            first_detected_at=now,
            last_detected_at=now,
            created_at=now,
            updated_at=now,
        )

        self.db.add(candidate)
        self.db.commit()
        self.db.refresh(candidate)

        return candidate

    def get_auto_register_targets(
        self,
        min_score: int,
        min_news_count: int,
        min_theme_count: int,
        limit: int,
    ):
        return (
            self.db.query(CandidateStock)
            .filter(CandidateStock.status == "CANDIDATE")
            .filter(CandidateStock.score >= min_score)
            .filter(CandidateStock.news_count >= min_news_count)
            .filter(CandidateStock.theme_keyword_count >= min_theme_count)
            .filter(CandidateStock.negative_keyword_count == 0)
            .order_by(CandidateStock.score.desc())
            .limit(limit)
            .all()
        )

    def get_auto_analysis_targets(self, limit: int):
        return (
            self.db.query(CandidateStock)
            .filter(CandidateStock.status == "AUTO_REGISTERED")
            .filter(CandidateStock.negative_keyword_count == 0)
            .order_by(
                CandidateStock.score.desc(),
                CandidateStock.last_detected_at.desc(),
            )
            .limit(limit)
            .all()
        )

    def mark_candidate(self, stock_code: str):
        candidate = (
            self.db.query(CandidateStock)
            .filter(CandidateStock.stock_code == stock_code)
            .first()
        )

        if not candidate:
            return

        candidate.status = "CANDIDATE"
        candidate.updated_at = datetime.utcnow()

        self.db.commit()

    def mark_auto_registered(self, stock_code: str):
        candidate = (
            self.db.query(CandidateStock)
            .filter(CandidateStock.stock_code == stock_code)
            .first()
        )

        if not candidate:
            return

        candidate.status = "AUTO_REGISTERED"
        candidate.updated_at = datetime.utcnow()

        self.db.commit()

    def mark_ai_analyzed(self, stock_code: str):
        candidate = (
            self.db.query(CandidateStock)
            .filter(CandidateStock.stock_code == stock_code)
            .first()
        )

        if not candidate:
            return

        candidate.status = "AI_ANALYZED"
        candidate.updated_at = datetime.utcnow()

        self.db.commit()

    def mark_price_filtered(self, stock_code: str):
        candidate = (
            self.db.query(CandidateStock)
            .filter(CandidateStock.stock_code == stock_code)
            .first()
        )

        if not candidate:
            return

        candidate.status = "PRICE_FILTERED"
        candidate.updated_at = datetime.utcnow()

        self.db.commit()

    def mark_risk_blocked(self, stock_code: str):
        candidate = (
            self.db.query(CandidateStock)
            .filter(CandidateStock.stock_code == stock_code)
            .first()
        )

        if not candidate:
            return

        candidate.status = "RISK_BLOCKED"
        candidate.updated_at = datetime.utcnow()

        self.db.commit()

    def cleanup_old_candidates(self, days: int, min_score: int) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)

        targets = (
            self.db.query(CandidateStock)
            .filter(CandidateStock.status.in_(["CANDIDATE", "RISK_BLOCKED", "PRICE_FILTERED"]))
            .filter(
                (CandidateStock.last_detected_at < cutoff)
                | (CandidateStock.score < min_score)
            )
            .all()
        )

        deleted_count = 0

        for target in targets:
            self.db.delete(target)
            deleted_count += 1

        self.db.commit()

        return deleted_count

    def get_recent_candidates(self, limit: int = 20):
        return (
            self.db.query(CandidateStock)
            .order_by(
                CandidateStock.score.desc(),
                CandidateStock.last_detected_at.desc(),
            )
            .limit(limit)
            .all()
        )
