import re

import httpx

from app.domains.news.application.port.naver_news_search_port import NaverNewsSearchPort
from app.domains.news.domain.entity.collected_news import CollectedNews


class NaverNewsClient(NaverNewsSearchPort):
    _BASE_URL = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret

    async def search(self, keyword: str, display: int = 100, start: int = 1) -> list[CollectedNews]:
        headers = {
            "X-Naver-Client-Id": self._client_id,
            "X-Naver-Client-Secret": self._client_secret,
        }
        params = {
            "query": keyword,
            "display": display,
            "start": start,
            "sort": "date",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(self._BASE_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        return [
            CollectedNews(
                title=self._strip_html(item.get("title", "")),
                description=self._strip_html(item.get("description", "")),
                url=item.get("originallink") or item.get("link", ""),
                published_at=item.get("pubDate", ""),
                keyword=keyword,
            )
            for item in data.get("items", [])
            if item.get("originallink") or item.get("link")
        ]

    @staticmethod
    def _strip_html(text: str) -> str:
        return re.sub(r"<[^>]+>", "", text).strip()
