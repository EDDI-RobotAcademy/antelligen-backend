from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response.base_response import BaseResponse
from app.domains.news.adapter.outbound.external.naver_news_client import NaverNewsClient
from app.domains.news.adapter.outbound.persistence.collected_news_repository_impl import (
    CollectedNewsRepositoryImpl,
)
from app.domains.news.application.response.collect_naver_news_response import CollectNaverNewsResponse
from app.domains.news.application.usecase.collect_naver_news_usecase import CollectNaverNewsUseCase
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.vector_database import get_vector_db

router = APIRouter(prefix="/news/collect", tags=["News Collection"])


@router.post("", response_model=BaseResponse[CollectNaverNewsResponse], status_code=201)
async def collect_naver_news(
    db: AsyncSession = Depends(get_vector_db),
):
    """인증 없이 네이버 뉴스 API로 경제/주식 키워드 뉴스를 수집하여 PostgreSQL에 저장한다."""
    settings = get_settings()
    naver_client = NaverNewsClient(
        client_id=settings.naver_client_id,
        client_secret=settings.naver_client_secret,
    )
    repository = CollectedNewsRepositoryImpl(db)
    usecase = CollectNaverNewsUseCase(naver_news_port=naver_client, repository=repository)
    result = await usecase.execute()
    return BaseResponse.ok(data=result)
