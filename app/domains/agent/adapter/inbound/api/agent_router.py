from fastapi import APIRouter

from app.common.response.base_response import BaseResponse
from app.domains.agent.adapter.outbound.external.mock_sub_agent_provider import (
    MockSubAgentProvider,
)
from app.domains.agent.adapter.outbound.external.openai_finance_agent_provider import (
    OpenAIFinanceAgentProvider,
)
from app.domains.agent.application.request.agent_query_request import AgentQueryRequest
from app.domains.agent.application.request.finance_analysis_request import (
    FinanceAnalysisRequest,
)
from app.domains.agent.application.response.frontend_agent_response import (
    FrontendAgentResponse,
)
from app.domains.agent.application.usecase.analyze_finance_agent_usecase import (
    AnalyzeFinanceAgentUseCase,
)
from app.domains.agent.application.usecase.process_agent_query_usecase import (
    ProcessAgentQueryUseCase,
)
from app.domains.stock.adapter.outbound.external.serp_stock_data_collector import (
    SerpStockDataCollector,
)
from app.domains.stock.adapter.outbound.external.opendart_financial_data_provider import (
    OpenDartFinancialDataProvider,
)
from app.domains.stock.adapter.outbound.persistence.corp_code_repository_impl import (
    CorpCodeRepositoryImpl,
)
from app.domains.stock.adapter.outbound.persistence.stock_repository_impl import (
    StockRepositoryImpl,
)
from app.domains.stock.adapter.outbound.persistence.stock_vector_repository_impl import (
    StockVectorRepositoryImpl,
)
from app.domains.stock.application.usecase.fetch_dart_financial_ratios_usecase import (
    FetchDartFinancialRatiosUseCase,
)
from app.domains.stock.application.usecase.collect_stock_data_usecase import (
    CollectStockDataUseCase,
)
from app.domains.stock.infrastructure.mapper.deterministic_stock_embedding_generator import (
    DeterministicStockEmbeddingGenerator,
)
from app.domains.stock.infrastructure.mapper.serp_stock_data_standardizer import (
    SerpStockDataStandardizer,
)
from app.domains.stock.infrastructure.mapper.simple_stock_document_chunker import (
    SimpleStockDocumentChunker,
)
from app.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post(
    "/query",
    response_model=BaseResponse[FrontendAgentResponse],
    status_code=200,
)
async def query_agent(request: AgentQueryRequest):
    provider = MockSubAgentProvider()
    usecase = ProcessAgentQueryUseCase(provider)
    internal_result = usecase.execute(request)
    frontend_result = FrontendAgentResponse.from_internal(internal_result)
    return BaseResponse.ok(data=frontend_result)


@router.post(
    "/finance-analysis",
    response_model=BaseResponse[FrontendAgentResponse],
    status_code=200,
)
async def analyze_finance(
    request: FinanceAnalysisRequest,
):
    settings = get_settings()
    stock_repository = StockRepositoryImpl()

    # DART 재무비율 UseCase (선택적)
    dart_financial_ratios_usecase = None
    if settings.dart_api_key:
        dart_financial_ratios_usecase = FetchDartFinancialRatiosUseCase(
            corp_code_repository=CorpCodeRepositoryImpl(),
            dart_financial_data_provider=OpenDartFinancialDataProvider(
                api_key=settings.dart_api_key
            ),
        )

    stock_collection_usecase = CollectStockDataUseCase(
        stock_repository=stock_repository,
        stock_data_collector=SerpStockDataCollector(api_key=settings.serp_api_key),
        stock_data_standardizer=SerpStockDataStandardizer(),
        stock_document_chunker=SimpleStockDocumentChunker(),
        stock_embedding_generator=DeterministicStockEmbeddingGenerator(),
        stock_vector_repository=StockVectorRepositoryImpl(),
        dart_financial_ratios_usecase=dart_financial_ratios_usecase,
    )
    finance_provider = OpenAIFinanceAgentProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_finance_agent_model,
    )
    usecase = AnalyzeFinanceAgentUseCase(
        stock_repository=stock_repository,
        stock_collection_usecase=stock_collection_usecase,
        finance_agent_provider=finance_provider,
    )
    internal_result = await usecase.execute(request)
    frontend_result = FrontendAgentResponse.from_internal(internal_result)
    return BaseResponse.ok(data=frontend_result)
