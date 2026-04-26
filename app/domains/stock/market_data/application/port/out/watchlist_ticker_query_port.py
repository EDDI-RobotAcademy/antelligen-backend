from abc import ABC, abstractmethod
from typing import List


class WatchlistTickerQueryPort(ABC):
    """user_watchlist 의 distinct stock_code 조회용 read-side 포트.

    account 도메인 ORM 직접 import를 피하기 위한 추상화.
    """

    @abstractmethod
    async def find_distinct_tickers(self) -> List[str]:
        ...
