from datetime import datetime


class CollectedNews:
    """네이버 뉴스 API로 수집한 뉴스 도메인 엔티티 — 순수 Python, 외부 의존성 없음"""

    def __init__(
        self,
        title: str,
        description: str,
        url: str,
        published_at: str,
        keyword: str,
        news_id: int | None = None,
        collected_at: datetime | None = None,
    ):
        self.news_id = news_id
        self.title = title
        self.description = description
        self.url = url
        self.published_at = published_at
        self.keyword = keyword
        self.collected_at = collected_at
