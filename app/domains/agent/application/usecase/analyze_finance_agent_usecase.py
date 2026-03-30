import uuid

from app.common.exception.app_exception import AppException
from app.domains.agent.application.port.finance_agent_provider import (
    FinanceAgentProvider,
)
from app.domains.agent.application.request.finance_analysis_request import (
    FinanceAnalysisRequest,
)
from app.domains.agent.application.response.agent_query_response import (
    AgentQueryResponse,
)
from app.domains.stock.application.usecase.collect_stock_data_usecase import (
    CollectStockDataUseCase,
)
from app.domains.stock.domain.entity.stock import Stock
from app.domains.stock.adapter.outbound.persistence.stock_repository_impl import (
    StockRepositoryImpl,
)


class AnalyzeFinanceAgentUseCase:
    def __init__(
        self,
        stock_repository: StockRepositoryImpl,
        stock_collection_usecase: CollectStockDataUseCase,
        finance_agent_provider: FinanceAgentProvider,
    ):
        self._stock_repository = stock_repository
        self._stock_collection_usecase = stock_collection_usecase
        self._finance_agent_provider = finance_agent_provider

    async def execute(self, request: FinanceAnalysisRequest) -> AgentQueryResponse:
        stock = await self._resolve_stock(request)
        stock_data = await self._stock_collection_usecase.execute(stock.ticker)
        finance_result = await self._finance_agent_provider.analyze(
            user_query=request.query,
            stock_data=stock_data,
        )

        return AgentQueryResponse(
            session_id=request.session_id or str(uuid.uuid4()),
            result_status=AgentQueryResponse.determine_status([finance_result]),
            answer=self._build_answer(finance_result),
            agent_results=[finance_result],
            total_execution_time_ms=finance_result.execution_time_ms,
        )

    async def _resolve_stock(self, request: FinanceAnalysisRequest) -> Stock:
        if request.ticker:
            stock = await self._stock_repository.find_by_ticker(request.ticker)
            if stock:
                return stock

        if request.company_name:
            stock = await self._stock_repository.find_by_company_name(request.company_name)
            if stock:
                return stock

        raise AppException(
            status_code=404,
            message="분석할 종목을 찾을 수 없습니다.",
        )

    def _build_answer(self, finance_result) -> str:
        signal = finance_result.get_investment_signal()
        if signal is None:
            return "재무분석 결과를 생성하지 못했습니다."

        points = " ".join(f"{index + 1}. {point}" for index, point in enumerate(signal.key_points))
        return f"{signal.summary} {points}".strip()
