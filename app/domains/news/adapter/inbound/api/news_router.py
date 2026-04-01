from fastapi import APIRouter, Query, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.agent.application.response.sub_agent_response import SubAgentResponse
from app.domains.news.adapter.outbound.external.article_content_scraper import (
    ArticleContentScraper,
)
from app.domains.news.adapter.outbound.external.openai_article_analysis_provider import (
    OpenAIArticleAnalysisProvider,
)
from app.domains.news.adapter.outbound.external.openai_news_signal_adapter import (
    OpenAINewsSignalAdapter,
)
from app.domains.news.adapter.outbound.external.serp_news_search_provider import (
    SerpNewsSearchProvider,
)
from app.domains.news.adapter.outbound.persistence.collected_news_repository_impl import (
    CollectedNewsRepositoryImpl,
)
from app.domains.news.adapter.outbound.persistence.saved_article_repository_impl import (
    SavedArticleRepositoryImpl,
)
from app.domains.news.application.request.save_article_request import (
    SaveArticleRequest,
)
from app.domains.news.application.request.search_news_request import SearchNewsRequest
from app.domains.news.application.response.analyze_article_response import (
    AnalyzeArticleResponse,
)
from app.domains.news.application.response.save_article_response import (
    SaveArticleResponse,
)
from app.domains.news.application.response.search_news_response import (
    SearchNewsResponse,
)
from app.domains.news.application.usecase.analyze_article_usecase import (
    AnalyzeArticleUseCase,
)
from app.domains.news.application.usecase.analyze_news_signal_usecase import (
    AnalyzeNewsSignalUseCase,
)
from app.domains.news.application.usecase.save_article_usecase import (
    SaveArticleUseCase,
)
from app.domains.news.application.usecase.search_news_usecase import SearchNewsUseCase
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db
from app.infrastructure.database.vector_database import get_vector_db

router = APIRouter(prefix="/news", tags=["News"])


@router.get("/search", response_model=BaseResponse[SearchNewsResponse])
async def search_news(
    keyword: str = Query(..., min_length=1, description="검색 키워드"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(10, ge=1, le=100, description="페이지 크기"),
):
    """인증 없이 뉴스를 검색하고 페이징된 결과를 반환한다."""
    settings = get_settings()
    provider = SerpNewsSearchProvider(api_key=settings.serp_api_key)
    usecase = SearchNewsUseCase(news_search_provider=provider)
    request = SearchNewsRequest(keyword=keyword, page=page, page_size=page_size)
    result = await usecase.execute(request)
    return BaseResponse.ok(data=result)


@router.post("/save", response_model=BaseResponse[SaveArticleResponse], status_code=201)
async def save_article(
    request: SaveArticleRequest,
    db: AsyncSession = Depends(get_db),
):
    """인증 없이 관심 기사를 저장한다. 링크에서 본문을 스크래핑하여 함께 저장한다."""
    repository = SavedArticleRepositoryImpl(db)
    content_provider = ArticleContentScraper()
    usecase = SaveArticleUseCase(repository=repository, content_provider=content_provider)
    result = await usecase.execute(request)
    return BaseResponse.ok(data=result)


@router.get("/analyze/{article_id}", response_model=BaseResponse[AnalyzeArticleResponse])
async def analyze_article(
    article_id: int = Path(..., ge=1, description="분석할 기사 ID"),
    db: AsyncSession = Depends(get_db),
):
    """저장된 기사의 핵심 키워드와 감정 분석 결과를 반환한다."""
    settings = get_settings()
    repository = SavedArticleRepositoryImpl(db)
    analysis_provider = OpenAIArticleAnalysisProvider(api_key=settings.openai_api_key)
    usecase = AnalyzeArticleUseCase(repository=repository, analysis_provider=analysis_provider)
    result = await usecase.execute(article_id)
    return BaseResponse.ok(data=result)


@router.get("/agent-result", response_model=BaseResponse[SubAgentResponse])
async def get_news_agent_result(
    ticker: str = Query(..., description="종목 코드 (예: 005930)"),
    db: AsyncSession = Depends(get_vector_db),
):
    """ticker 기반으로 수집된 뉴스를 GPT로 감성 분석하여 투자 신호를 반환한다."""
    settings = get_settings()
    repository = CollectedNewsRepositoryImpl(db)
    analysis_adapter = OpenAINewsSignalAdapter(api_key=settings.openai_api_key)
    usecase = AnalyzeNewsSignalUseCase(repository=repository, analysis_port=analysis_adapter)
    result = await usecase.execute(ticker)
    return BaseResponse.ok(data=result)