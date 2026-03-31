from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.market_analysis.adapter.outbound.external.langchain_llm_adapter import LangChainLLMAdapter
from app.domains.market_analysis.adapter.outbound.persistence.market_context_repository_impl import MarketContextRepositoryImpl
from app.domains.market_analysis.application.request.analyze_question_request import AnalyzeQuestionRequest
from app.domains.market_analysis.application.usecase.analyze_market_question_usecase import AnalyzeMarketQuestionUseCase
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.database.database import get_db
from app.infrastructure.external.langchain_llm_client import get_langchain_llm_client

router = APIRouter(prefix="/market-analysis", tags=["market-analysis"])


@router.post("/ask")
async def ask_market_question(
    request: AnalyzeQuestionRequest,
    user_token: Optional[str] = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not user_token:
        raise AppException(status_code=401, message="인증이 필요합니다.")

    account_id_str = await redis.get(f"session:{user_token}")
    if not account_id_str:
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")

    context_repo = MarketContextRepositoryImpl(db)
    llm_adapter = LangChainLLMAdapter(get_langchain_llm_client())
    response = await AnalyzeMarketQuestionUseCase(context_repo, llm_adapter).execute(request)

    return BaseResponse.ok(data=response, message="분석 완료")
