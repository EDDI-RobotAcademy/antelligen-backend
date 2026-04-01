from abc import ABC, abstractmethod

from app.domains.news.domain.entity.collected_news import CollectedNews


class CollectedNewsRepositoryPort(ABC):

    @abstractmethod
    async def save(self, news: CollectedNews) -> CollectedNews:
        pass

    @abstractmethod
    async def exists_by_url(self, url: str) -> bool:
        pass

    @abstractmethod
    async def find_by_keyword(self, keyword: str, limit: int = 20) -> list[CollectedNews]:
        pass
