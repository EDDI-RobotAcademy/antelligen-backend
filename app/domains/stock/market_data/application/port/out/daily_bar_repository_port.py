from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from app.domains.stock.market_data.domain.entity.daily_bar import DailyBar


class DailyBarRepositoryPort(ABC):

    @abstractmethod
    async def upsert_bulk(self, bars: List[DailyBar]) -> int:
        ...

    @abstractmethod
    async def find_range(
        self, ticker: str, start: date, end: date
    ) -> List[DailyBar]:
        ...

    @abstractmethod
    async def find_around(
        self,
        ticker: str,
        event_date: date,
        before_days: int,
        after_days: int,
    ) -> List[DailyBar]:
        ...

    @abstractmethod
    async def find_latest_bar_date(self, ticker: str) -> Optional[date]:
        ...

    @abstractmethod
    async def find_distinct_tickers(self) -> List[str]:
        ...
