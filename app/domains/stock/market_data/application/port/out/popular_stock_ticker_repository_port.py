from abc import ABC, abstractmethod
from typing import List

from app.domains.stock.market_data.domain.entity.popular_stock_ticker import (
    PopularStockTicker,
)


class PopularStockTickerRepositoryPort(ABC):

    @abstractmethod
    async def find_all(self) -> List[PopularStockTicker]:
        ...

    @abstractmethod
    async def find_by_region(self, region: str) -> List[PopularStockTicker]:
        ...
