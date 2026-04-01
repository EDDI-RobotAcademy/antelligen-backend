from app.domains.news.application.port.collected_news_repository_port import CollectedNewsRepositoryPort
from app.domains.news.application.port.naver_news_search_port import NaverNewsSearchPort
from app.domains.news.application.response.collect_naver_news_response import (
    CollectNaverNewsResponse,
    CollectedNewsItemResponse,
)

COLLECTION_KEYWORDS = [
    "코스피", "코스닥", "삼성전자", "SK하이닉스", "현대차",
    "금리", "환율", "반도체", "2차전지", "AI",
]


class CollectNaverNewsUseCase:
    def __init__(
        self,
        naver_news_port: NaverNewsSearchPort,
        repository: CollectedNewsRepositoryPort,
    ):
        self._naver_news_port = naver_news_port
        self._repository = repository

    async def execute(self) -> CollectNaverNewsResponse:
        collected: list[CollectedNewsItemResponse] = []
        skipped = 0

        for keyword in COLLECTION_KEYWORDS:
            for page in range(10):  # 100개 × 10페이지 = 키워드당 최대 1000건
                start = page * 100 + 1
                articles = await self._naver_news_port.search(keyword=keyword, display=100, start=start)
                if not articles:
                    break
                for article in articles:
                    if await self._repository.exists_by_url(article.url):
                        skipped += 1
                        continue
                    saved = await self._repository.save(article)
                    collected.append(
                        CollectedNewsItemResponse(
                            title=saved.title,
                            description=saved.description,
                            url=saved.url,
                            published_at=saved.published_at,
                            keyword=saved.keyword,
                        )
                    )

        return CollectNaverNewsResponse(
            total_collected=len(collected),
            skipped_duplicates=skipped,
            items=collected,
        )
