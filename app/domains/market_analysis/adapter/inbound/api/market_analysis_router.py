import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.market_analysis.adapter.outbound.external.langchain_analysis_adapter import LangChainAnalysisAdapter
from app.domains.market_analysis.adapter.outbound.persistence.market_data_repository_impl import MarketDataRepositoryImpl
from app.domains.market_analysis.application.request.analyze_question_request import AnalyzeQuestionRequest
from app.domains.market_analysis.application.response.analyze_question_response import AnalyzeQuestionResponse
from app.domains.market_analysis.application.usecase.analyze_question_usecase import AnalyzeQuestionUseCase
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/market-analysis", tags=["market-analysis"])

_SESSION_KEY_PREFIX = "session:"


@router.post("/analyze", response_model=BaseResponse[AnalyzeQuestionResponse])
async def analyze_question(
    request: AnalyzeQuestionRequest,
    user_token: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not user_token:
        raise AppException(status_code=401, message="인증이 필요합니다.")

    account_id_str = await redis.get(f"{_SESSION_KEY_PREFIX}{user_token}")
    if not account_id_str:
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")

    settings = get_settings()
    market_data_repo = MarketDataRepositoryImpl(db)
    llm_chain = LangChainAnalysisAdapter(api_key=settings.openai_api_key)
    usecase = AnalyzeQuestionUseCase(market_data_repo, llm_chain)
    response = await usecase.execute(request)

    return BaseResponse.ok(data=response, message="분석 완료")
