from abc import ABC, abstractmethod

from app.domains.news.domain.entity.collected_news import CollectedNews


class NaverNewsSearchPort(ABC):

    @abstractmethod
    async def search(self, keyword: str, display: int = 100, start: int = 1) -> list[CollectedNews]:
        pass
