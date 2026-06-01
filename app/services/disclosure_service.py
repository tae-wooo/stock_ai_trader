from datetime import datetime

from app.collectors.dart_collector import DartCollector
from app.database.models import Disclosure


class DisclosureService:
    def __init__(self, db):
        self.db = db
        self.collector = DartCollector()

    def collect_and_save(
        self,
        stock_code: str,
        bgn_de: str | None = None,
        end_de: str | None = None,
    ):
        disclosures = self.collector.get_disclosures(
            stock_code=stock_code,
            bgn_de=bgn_de,
            end_de=end_de,
            page_count=20,
        )

        saved_count = 0

        for item in disclosures:
            report_no = item.get("rcept_no")

            if not report_no:
                continue

            exists = (
                self.db.query(Disclosure)
                .filter(Disclosure.report_no == report_no)
                .first()
            )

            if exists:
                continue

            published_at = None
            if item.get("rcept_dt"):
                try:
                    published_at = datetime.strptime(item["rcept_dt"], "%Y%m%d")
                except Exception:
                    published_at = None

            dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={report_no}"

            disclosure = Disclosure(
                stock_code=stock_code,
                report_no=report_no,
                title=item.get("report_nm", ""),
                report_type=item.get("report_nm", ""),
                dart_url=dart_url,
                published_at=published_at,
            )

            self.db.add(disclosure)
            saved_count += 1

        self.db.commit()
        return saved_count
