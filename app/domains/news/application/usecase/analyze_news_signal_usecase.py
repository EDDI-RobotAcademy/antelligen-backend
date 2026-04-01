import time

from app.domains.agent.application.response.sub_agent_response import SubAgentResponse
from app.domains.news.application.port.collected_news_repository_port import CollectedNewsRepositoryPort
from app.domains.news.application.port.news_signal_analysis_port import NewsSignalAnalysisPort

# 종목코드 → 수집 키워드 매핑 (CollectNaverNewsUseCase의 COLLECTION_KEYWORDS 기준)
TICKER_TO_KEYWORDS: dict[str, list[str]] = {
    "005930": ["삼성전자"],
    "000660": ["SK하이닉스"],
    "005380": ["현대차"],
    "035420": ["네이버"],
    "035720": ["카카오"],
    "068270": ["셀트리온"],
    "207940": ["삼성바이오로직스"],
    "005490": ["포스코"],
}


class AnalyzeNewsSignalUseCase:
    def __init__(
        self,
        repository: CollectedNewsRepositoryPort,
        analysis_port: NewsSignalAnalysisPort,
    ):
        self._repository = repository
        self._analysis_port = analysis_port

    async def execute(self, ticker: str) -> SubAgentResponse:
        start_ms = int(time.time() * 1000)
        keywords = TICKER_TO_KEYWORDS.get(ticker, [])

        all_articles = []
        for keyword in keywords:
            articles = await self._repository.find_by_keyword(keyword, limit=20)
            all_articles.extend(articles)

        elapsed_ms = int(time.time() * 1000) - start_ms

        if not all_articles:
            return SubAgentResponse.no_data("news", elapsed_ms)

        company_name = keywords[0] if keywords else ticker

        try:
            signal = await self._analysis_port.analyze(ticker, company_name, all_articles)
        except Exception:
            elapsed_ms = int(time.time() * 1000) - start_ms
            return SubAgentResponse.error("news", "뉴스 감성 분석 중 오류가 발생했습니다.", elapsed_ms)

        elapsed_ms = int(time.time() * 1000) - start_ms
        return SubAgentResponse.success_with_signal(signal, {"ticker": ticker}, elapsed_ms)
