from abc import ABC, abstractmethod

from app.domains.news.application.response.analyze_article_response import (
    AnalyzeArticleResponse,
)


class ArticleAnalysisProvider(ABC):

    @abstractmethod
    async def analyze(self, article_id: int, content: str) -> AnalyzeArticleResponse:
        pass
