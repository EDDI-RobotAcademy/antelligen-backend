from abc import ABC, abstractmethod

from app.domains.agent.application.response.investment_signal_response import InvestmentSignalResponse
from app.domains.news.domain.entity.collected_news import CollectedNews


class NewsSignalAnalysisPort(ABC):

    @abstractmethod
    async def analyze(
        self, ticker: str, company_name: str, articles: list[CollectedNews]
    ) -> InvestmentSignalResponse:
        pass
