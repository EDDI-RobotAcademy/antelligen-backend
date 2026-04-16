from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.agent.adapter.outbound.cache.redis_finance_analysis_cache import (
    RedisFinanceAnalysisCache,
)
from app.domains.agent.adapter.outbound.external.disclosure_sub_agent_adapter import (
    DisclosureSubAgentAdapter,
)
from app.domains.agent.adapter.outbound.external.finance_sub_agent_adapter import (
    FinanceSubAgentAdapter,
)
from app.domains.agent.adapter.outbound.external.langgraph_finance_agent_provider import (
    LangGraphFinanceAgentProvider,
)
from app.domains.agent.adapter.outbound.external.news_sub_agent_adapter import (
    NewsSubAgentAdapter,
)
from app.domains.agent.adapter.outbound.external.openai_synthesis_client import (
    OpenAISynthesisClient,
)
from app.domains.agent.adapter.outbound.persistence.integrated_analysis_repository_impl import (
    IntegratedAnalysisRepositoryImpl,
)
from app.domains.agent.application.request.agent_query_request import AgentQueryRequest
from app.domains.agent.application.request.finance_analysis_request import (
    FinanceAnalysisRequest,
)
from app.domains.agent.application.response.frontend_agent_response import (
    FrontendAgentResponse,
)
from app.domains.agent.application.response.integrated_analysis_response import (
    IntegratedAnalysisResponse,
)
from app.domains.agent.application.usecase.analyze_finance_agent_usecase import (
    AnalyzeFinanceAgentUseCase,
)
from app.domains.agent.application.usecase.process_agent_query_usecase import (
    ProcessAgentQueryUseCase,
)
from app.domains.stock.adapter.outbound.persistence.stock_repository_impl import (
    StockRepositoryImpl,
)
from app.domains.stock.adapter.outbound.persistence.stock_vector_repository_impl import (
    StockVectorRepositoryImpl,
)
from app.domains.stock.application.usecase.get_stored_stock_data_usecase import (
    GetStoredStockDataUseCase,
)
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

SESSION_KEY_PREFIX = "session:"

router = APIRouter(prefix="/agent", tags=["Agent"])


async def _require_auth(request: Request, redis: aioredis.Redis) -> None:
    """쿠키 → Authorization 헤더 순으로 토큰을 확인합니다."""
    token = request.cookies.get("user_token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip() or None
    if not token:
        raise AppException(status_code=401, message="인증이 필요합니다.")
    if not await redis.get(f"{SESSION_KEY_PREFIX}{token}"):
        raise AppException(status_code=401, message="세션이 만료되었거나 유효하지 않습니다.")


@router.post(
    "/query",
    response_model=BaseResponse[FrontendAgentResponse],
    status_code=200,
)
async def query_agent(
    request: Request,
    body: AgentQueryRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    await _require_auth(request, redis)

    settings = get_settings()
    repository = IntegratedAnalysisRepositoryImpl(db)
    llm_synthesis = OpenAISynthesisClient(api_key=settings.openai_api_key)

    usecase = ProcessAgentQueryUseCase(
        news_agent=NewsSubAgentAdapter(db=db, api_key=settings.openai_api_key),
        disclosure_agent=DisclosureSubAgentAdapter(),
        finance_agent=FinanceSubAgentAdapter(),
        llm_synthesis=llm_synthesis,
        repository=repository,
    )
    internal_result = await usecase.execute(body)
    frontend_result = FrontendAgentResponse.from_internal(internal_result)
    return BaseResponse.ok(data=frontend_result)


@router.get(
    "/history",
    response_model=BaseResponse[list[IntegratedAnalysisResponse]],
    status_code=200,
)
async def get_analysis_history(
    request: Request,
    ticker: str = Query(..., description="종목 코드 (예: 005930)"),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """ticker 기준 최근 통합 분석 이력을 반환합니다."""
    await _require_auth(request, redis)

    repository = IntegratedAnalysisRepositoryImpl(db)
    history = await repository.find_history(ticker, limit=limit)
    return BaseResponse.ok(data=history)


@router.post(
    "/finance-analysis",
    response_model=BaseResponse[FrontendAgentResponse],
    status_code=200,
)
async def analyze_finance(
    request: FinanceAnalysisRequest,
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    벡터 DB에 저장된 데이터를 기반으로 재무 분석을 수행합니다.
    먼저 /stock/{ticker}/collect로 데이터를 적재해야 합니다.
    """
    settings = get_settings()
    stock_repository = StockRepositoryImpl()
    stock_vector_repository = StockVectorRepositoryImpl()

    get_stored_stock_data_usecase = GetStoredStockDataUseCase(
        stock_repository=stock_repository,
        stock_vector_repository=stock_vector_repository,
    )

    finance_provider = LangGraphFinanceAgentProvider(
        api_key=settings.openai_api_key,
        chat_model=settings.openai_finance_agent_model,
        embedding_model=settings.openai_embedding_model,
        top_k=settings.finance_rag_top_k,
        langsmith_tracing=settings.langsmith_tracing,
        langsmith_api_key=settings.langsmith_api_key,
        langsmith_project=settings.langsmith_project,
        langsmith_endpoint=settings.langsmith_endpoint,
    )

    usecase = AnalyzeFinanceAgentUseCase(
        stock_repository=stock_repository,
        get_stored_stock_data_usecase=get_stored_stock_data_usecase,
        finance_agent_provider=finance_provider,
        finance_analysis_cache=RedisFinanceAnalysisCache(
            redis=redis,
            ttl_seconds=settings.finance_analysis_cache_ttl_seconds,
        ),
    )
    internal_result = await usecase.execute(request)
    frontend_result = FrontendAgentResponse.from_internal(internal_result)
    return BaseResponse.ok(data=frontend_result)
