from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from app.domains.stock.market_data.domain.entity.daily_bar import DailyBar


class DailyBarFetcherPort(ABC):
    """외부 시세 소스(yfinance/Polygon 등) 추상화. 적재 잡과 cached decorator의 fallback에서 사용."""

    @abstractmethod
    async def fetch(
        self,
        ticker: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        period: Optional[str] = None,
    ) -> List[DailyBar]:
        """start/end 또는 period 중 하나로 일봉 조회.

        period: yfinance 스타일 ("max", "5d", "1y" 등). start/end 우선 사용.
        """
        ...
