import io
import json
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

from app.config.settings import settings


class DartCollector:
    DISCLOSURE_URL = "https://opendart.fss.or.kr/api/list.json"
    CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"

    CACHE_PATH = Path("data/raw/dart_corp_codes.json")

    def _download_and_cache_corp_codes(self):
        if not settings.DART_API_KEY:
            raise ValueError("DART_API_KEY가 .env에 설정되어 있지 않습니다.")

        params = {
            "crtfc_key": settings.DART_API_KEY,
        }

        response = requests.get(
            self.CORP_CODE_URL,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        xml_filename = zip_file.namelist()[0]
        xml_data = zip_file.read(xml_filename)

        root = ET.fromstring(xml_data)

        corp_codes = []

        for item in root.findall("list"):
            corp_code = item.findtext("corp_code")
            corp_name = item.findtext("corp_name")
            stock_code = item.findtext("stock_code")
            modify_date = item.findtext("modify_date")

            if stock_code:
                corp_codes.append(
                    {
                        "corp_code": corp_code,
                        "corp_name": corp_name,
                        "stock_code": stock_code,
                        "modify_date": modify_date,
                    }
                )

        self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(self.CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(corp_codes, f, ensure_ascii=False, indent=2)

        return corp_codes

    def _load_corp_codes(self):
        if not self.CACHE_PATH.exists():
            return self._download_and_cache_corp_codes()

        with open(self.CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_corp_code_by_stock_code(self, stock_code: str) -> str:
        corp_codes = self._load_corp_codes()

        for item in corp_codes:
            if item["stock_code"] == stock_code:
                return item["corp_code"]

        raise ValueError(f"DART 고유번호를 찾을 수 없습니다. stock_code={stock_code}")

    def get_disclosures(
        self,
        stock_code: str,
        bgn_de: str | None = None,
        end_de: str | None = None,
        page_count: int = 20,
    ):
        if not settings.DART_API_KEY:
            raise ValueError("DART_API_KEY가 .env에 설정되어 있지 않습니다.")

        corp_code = self.get_corp_code_by_stock_code(stock_code)

        params = {
            "crtfc_key": settings.DART_API_KEY,
            "corp_code": corp_code,
            "page_count": page_count,
            "sort": "date",
            "sort_mth": "desc",
        }

        if bgn_de:
            params["bgn_de"] = bgn_de

        if end_de:
            params["end_de"] = end_de

        response = requests.get(
            self.DISCLOSURE_URL,
            params=params,
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()

        status = data.get("status")
        message = data.get("message")

        if status == "013":
            print("조회된 공시가 없습니다.")
            return []

        if status != "000":
            raise ValueError(f"DART API 오류: {status} / {message}")

        return data.get("list", [])
