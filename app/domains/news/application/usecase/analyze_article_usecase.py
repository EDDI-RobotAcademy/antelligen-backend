from app.common.exception.app_exception import AppException
from app.domains.news.application.port.article_analysis_provider import (
    ArticleAnalysisProvider,
)
from app.domains.news.application.port.saved_article_repository import (
    SavedArticleRepository,
)
from app.domains.news.application.response.analyze_article_response import (
    AnalyzeArticleResponse,
)


class AnalyzeArticleUseCase:
    def __init__(
        self,
        repository: SavedArticleRepository,
        analysis_provider: ArticleAnalysisProvider,
    ):
        self._repository = repository
        self._analysis_provider = analysis_provider

    async def execute(self, article_id: int) -> AnalyzeArticleResponse:
        article = await self._repository.find_by_id(article_id)
        if article is None:
            raise AppException(status_code=404, message=f"기사를 찾을 수 없습니다. (ID: {article_id})")

        if not article.content:
            raise AppException(status_code=422, message="기사 본문이 없어 분석할 수 없습니다.")

        return await self._analysis_provider.analyze(
            article_id=article_id,
            content=article.content,
        )
