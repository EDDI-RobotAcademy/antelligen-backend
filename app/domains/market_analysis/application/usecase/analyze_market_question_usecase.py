from app.domains.market_analysis.application.port.out.llm_port import LLMPort
from app.domains.market_analysis.application.port.out.market_context_port import MarketContextPort
from app.domains.market_analysis.application.request.analyze_question_request import AnalyzeQuestionRequest
from app.domains.market_analysis.application.response.analyze_question_response import AnalyzeQuestionResponse
from app.domains.market_analysis.domain.service.context_builder import ContextBuilder


class AnalyzeMarketQuestionUseCase:
    def __init__(self, context_port: MarketContextPort, llm_port: LLMPort):
        self._context_port = context_port
        self._llm_port = llm_port

    async def execute(self, request: AnalyzeQuestionRequest) -> AnalyzeQuestionResponse:
        keywords = await self._context_port.get_top_keywords(top_n=30)
        stock_themes = await self._context_port.get_stock_themes()
        context = ContextBuilder.build(keywords, stock_themes)
        answer = await self._llm_port.generate_answer(request.question, context)
        return AnalyzeQuestionResponse(answer=answer)
