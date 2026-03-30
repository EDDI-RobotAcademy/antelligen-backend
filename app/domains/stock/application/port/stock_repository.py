from abc import ABC, abstractmethod
from typing import Optional

from app.domains.stock.domain.entity.stock import Stock


class StockRepository(ABC):

    @abstractmethod
    async def find_by_ticker(self, ticker: str) -> Optional[Stock]:
        pass

    @abstractmethod
    async def find_by_company_name(self, company_name: str) -> Optional[Stock]:
        pass
