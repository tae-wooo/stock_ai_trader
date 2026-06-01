from email.utils import parsedate_to_datetime

from app.collectors.naver_news_collector import NaverNewsCollector
from app.database.models import News
from app.utils.text_cleaner import clean_html


class NewsService:
    def __init__(self, db):
        self.db = db
        self.collector = NaverNewsCollector()

    def collect_and_save(self, stock_code: str, keyword: str, display: int = 10):
        items = self.collector.search_news(keyword=keyword, display=display)
        saved_count = 0

        for item in items:
            link = item.get("link")

            if not link:
                continue

            exists = self.db.query(News).filter(News.link == link).first()
            if exists:
                continue

            published_at = None
            if item.get("pubDate"):
                try:
                    published_at = parsedate_to_datetime(item["pubDate"])
                except Exception:
                    published_at = None

            news = News(
                stock_code=stock_code,
                title=clean_html(item.get("title", "")),
                link=link,
                description=clean_html(item.get("description", "")),
                published_at=published_at,
            )

            self.db.add(news)
            saved_count += 1

        self.db.commit()
        return saved_count
