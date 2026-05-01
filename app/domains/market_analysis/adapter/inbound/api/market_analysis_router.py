from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, Request
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

SESSION_KEY_PREFIX = "session:"
TEMP_TOKEN_KEY_PREFIX = "temp_token:"


async def _resolve_token(request: Request, redis: aioredis.Redis) -> None:
    """쿠키(user_token/temp_token) 또는 Authorization Bearer 헤더로 인증을 확인한다."""
    user_token = request.cookies.get("user_token")
    temp_token = request.cookies.get("temp_token")
    auth_header = request.headers.get("authorization", "")

    if not user_token and auth_header.startswith("Bearer "):
        user_token = auth_header.removeprefix("Bearer ").strip() or None

    if not user_token and not temp_token:
        raise AppException(status_code=401, message="인증이 필요합니다.")

    if user_token:
        if await redis.get(f"{SESSION_KEY_PREFIX}{user_token}"):
            return

    if temp_token:
        if await redis.get(f"{TEMP_TOKEN_KEY_PREFIX}{temp_token}"):
            return

    raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")


@router.post("/ask")
async def ask_market_question(
    body: AnalyzeQuestionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    await _resolve_token(request, redis)

    context_repo = MarketContextRepositoryImpl(db)
    llm_adapter = LangChainLLMAdapter(get_langchain_llm_client())
    response = await AnalyzeMarketQuestionUseCase(context_repo, llm_adapter).execute(body)

    return BaseResponse.ok(data=response, message="분석 완료")
