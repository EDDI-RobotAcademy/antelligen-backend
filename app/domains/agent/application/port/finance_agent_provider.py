from abc import ABC, abstractmethod

from app.domains.agent.application.response.sub_agent_response import SubAgentResponse
from app.domains.stock.application.response.stock_collection_response import (
    StockCollectionResponse,
)


class FinanceAgentProvider(ABC):
    @abstractmethod
    async def analyze(
        self,
        *,
        user_query: str,
        stock_data: StockCollectionResponse,
    ) -> SubAgentResponse:
        pass
