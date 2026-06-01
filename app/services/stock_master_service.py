import io
import zipfile
import xml.etree.ElementTree as ET

import requests

from app.config.settings import settings
from app.database.models import StockMaster


class StockMasterService:
    CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"

    def __init__(self, db):
        self.db = db

    def _download_dart_corp_codes(self) -> list[dict]:
        """
        DART corpCode.xml을 내려받아 상장회사 종목코드/회사명을 가져온다.
        stock_code가 있는 회사만 반환한다.
        """

        if not settings.DART_API_KEY:
            raise ValueError("DART_API_KEY가 .env에 설정되어 있지 않습니다.")

        response = requests.get(
            self.CORP_CODE_URL,
            params={"crtfc_key": settings.DART_API_KEY},
            timeout=20,
        )

        response.raise_for_status()

        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        xml_filename = zip_file.namelist()[0]
        xml_data = zip_file.read(xml_filename)

        root = ET.fromstring(xml_data)

        companies = []

        for item in root.findall("list"):
            corp_code = item.findtext("corp_code")
            corp_name = item.findtext("corp_name")
            stock_code = item.findtext("stock_code")
            modify_date = item.findtext("modify_date")

            if not stock_code:
                continue

            stock_code = stock_code.strip()
            corp_name = corp_name.strip() if corp_name else ""

            if not stock_code or not corp_name:
                continue

            companies.append(
                {
                    "corp_code": corp_code,
                    "code": stock_code,
                    "name": corp_name,
                    "market": "DART",
                    "modify_date": modify_date,
                }
            )

        return companies

    def sync_stock_master(self):
        """
        DART에서 상장회사 목록을 가져와 stock_master 테이블에 저장한다.
        이미 있으면 이름/시장 정보를 업데이트한다.
        """

        companies = self._download_dart_corp_codes()

        saved_count = 0
        updated_count = 0

        for company in companies:
            exists = (
                self.db.query(StockMaster)
                .filter(StockMaster.code == company["code"])
                .first()
            )

            if exists:
                exists.name = company["name"]
                exists.market = company["market"]
                updated_count += 1
                continue

            stock_master = StockMaster(
                code=company["code"],
                name=company["name"],
                market=company["market"],
            )

            self.db.add(stock_master)
            saved_count += 1

        self.db.commit()

        print(f"신규 저장: {saved_count}개")
        print(f"기존 업데이트: {updated_count}개")

        return saved_count

    def get_all(self):
        return self.db.query(StockMaster).all()

    def find_by_name_in_text(
        self,
        text: str,
        min_name_length: int = 3,
        ignore_names: list[str] | None = None,
    ):
        """
        뉴스 제목/요약에 포함된 종목명을 찾는다.
        너무 짧거나 일반 단어와 겹치는 종목명은 오탐 가능성이 높아서 제외한다.
        """

        ignore_names = ignore_names or []

        stocks = self.get_all()
        matched = []

        for item in stocks:
            if not item.name:
                continue

            if len(item.name) < min_name_length:
                continue

            if item.name in ignore_names:
                continue

            if item.name in text:
                matched.append(item)

        return matched

    def find_by_code(self, code: str):
        return (
            self.db.query(StockMaster)
            .filter(StockMaster.code == code)
            .first()
        )
