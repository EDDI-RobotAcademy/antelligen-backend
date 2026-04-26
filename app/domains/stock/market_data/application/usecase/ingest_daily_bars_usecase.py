import asyncio
import logging
from datetime import date
from typing import List, Optional

from app.domains.stock.market_data.application.port.out.daily_bar_fetcher_port import (
    DailyBarFetcherPort,
)
from app.domains.stock.market_data.application.port.out.daily_bar_repository_port import (
    DailyBarRepositoryPort,
)

logger = logging.getLogger(__name__)


class IngestDailyBarsUseCase:
    """ticker 목록의 일봉을 yfinance에서 fetch해 DB에 upsert.

    period(yfinance 스타일 "max"/"5d") 또는 (start, end) 둘 중 하나로 호출.
    """

    def __init__(
        self,
        fetcher: DailyBarFetcherPort,
        repository: DailyBarRepositoryPort,
    ):
        self._fetcher = fetcher
        self._repository = repository

    async def execute(
        self,
        tickers: List[str],
        period: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        concurrency: int = 4,
    ) -> int:
        if not tickers:
            return 0

        sem = asyncio.Semaphore(concurrency)

        async def _fetch_one(ticker: str):
            async with sem:
                try:
                    return await self._fetcher.fetch(
                        ticker=ticker, start=start, end=end, period=period
                    )
                except Exception as e:
                    logger.warning(
                        "[IngestDailyBars] fetch 실패 (graceful): ticker=%s err=%s",
                        ticker, e,
                    )
                    return []

        results = await asyncio.gather(
            *[_fetch_one(t) for t in tickers], return_exceptions=False
        )

        all_bars = [bar for bars in results for bar in bars]
        if not all_bars:
            logger.info("[IngestDailyBars] 적재 대상 없음 (tickers=%d)", len(tickers))
            return 0

        saved = await self._repository.upsert_bulk(all_bars)
        logger.info(
            "[IngestDailyBars] 완료: tickers=%d fetched=%d saved=%d",
            len(tickers), len(all_bars), saved,
        )
        return saved
