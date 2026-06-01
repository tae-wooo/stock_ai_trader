import requests

from app.config.settings import settings


class NaverNewsCollector:
    BASE_URL = "https://openapi.naver.com/v1/search/news.json"

    def search_news(
        self,
        keyword: str,
        display: int = 10,
        start: int = 1,
        sort: str = "date",
    ):
        if not settings.NAVER_CLIENT_ID or not settings.NAVER_CLIENT_SECRET:
            raise ValueError("네이버 API 키가 .env에 설정되어 있지 않습니다.")

        headers = {
            "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
        }

        params = {
            "query": keyword,
            "display": display,
            "start": start,
            "sort": sort,
        }

        response = requests.get(
            self.BASE_URL,
            headers=headers,
            params=params,
            timeout=10,
        )

        response.raise_for_status()
        return response.json().get("items", [])
