from app.domains.market_analysis.application.port.out.llm_chain_port import LlmChainPort
from app.domains.market_analysis.application.port.out.market_data_port import MarketDataPort
from app.domains.market_analysis.application.request.analyze_question_request import AnalyzeQuestionRequest
from app.domains.market_analysis.application.response.analyze_question_response import AnalyzeQuestionResponse
from app.domains.market_analysis.domain.service.market_context_builder import MarketContextBuilder


class AnalyzeQuestionUseCase:
    def __init__(self, market_data_port: MarketDataPort, llm_chain_port: LlmChainPort):
        self._market_data_port = market_data_port
        self._llm_chain_port = llm_chain_port

    async def execute(self, request: AnalyzeQuestionRequest) -> AnalyzeQuestionResponse:
        stocks = await self._market_data_port.fetch_all_defense_stocks()
        context = MarketContextBuilder.build(stocks)
        answer = await self._llm_chain_port.analyze(question=request.question, context=context)
        return AnalyzeQuestionResponse(answer=answer)
