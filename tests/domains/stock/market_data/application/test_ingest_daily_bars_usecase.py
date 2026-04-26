"""IngestDailyBarsUseCase — fetcher/repository 모두 mock으로 흐름 검증."""
import asyncio
from datetime import date
from typing import List, Optional

from app.domains.stock.market_data.application.port.out.daily_bar_fetcher_port import (
    DailyBarFetcherPort,
)
from app.domains.stock.market_data.application.port.out.daily_bar_repository_port import (
    DailyBarRepositoryPort,
)
from app.domains.stock.market_data.application.usecase.ingest_daily_bars_usecase import (
    IngestDailyBarsUseCase,
)
from app.domains.stock.market_data.domain.entity.daily_bar import DailyBar


class _StubFetcher(DailyBarFetcherPort):
    def __init__(self, by_ticker: dict):
        self._by_ticker = by_ticker
        self.calls: list[tuple[str, Optional[str]]] = []

    async def fetch(
        self,
        ticker: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        period: Optional[str] = None,
    ) -> List[DailyBar]:
        self.calls.append((ticker, period))
        if isinstance(self._by_ticker.get(ticker), Exception):
            raise self._by_ticker[ticker]
        return list(self._by_ticker.get(ticker, []))


class _StubRepo(DailyBarRepositoryPort):
    def __init__(self):
        self.upserted: List[DailyBar] = []

    async def upsert_bulk(self, bars: List[DailyBar]) -> int:
        self.upserted.extend(bars)
        return len(bars)

    async def find_range(self, ticker, start, end):
        return []

    async def find_around(self, ticker, event_date, before_days, after_days):
        return []

    async def find_latest_bar_date(self, ticker):
        return None

    async def find_distinct_tickers(self):
        return []


def _bar(ticker: str, d: date, close: float = 100.0) -> DailyBar:
    return DailyBar(
        ticker=ticker,
        bar_date=d,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000,
    )


def test_executes_empty_ticker_list_returns_zero():
    repo = _StubRepo()
    usecase = IngestDailyBarsUseCase(_StubFetcher({}), repo)

    saved = asyncio.run(usecase.execute(tickers=[], period="5d"))

    assert saved == 0
    assert repo.upserted == []


def test_aggregates_bars_from_multiple_tickers_into_single_upsert():
    fetcher = _StubFetcher(
        {
            "AAPL": [_bar("AAPL", date(2026, 4, 1)), _bar("AAPL", date(2026, 4, 2))],
            "NVDA": [_bar("NVDA", date(2026, 4, 1))],
        }
    )
    repo = _StubRepo()
    usecase = IngestDailyBarsUseCase(fetcher, repo)

    saved = asyncio.run(usecase.execute(tickers=["AAPL", "NVDA"], period="5d"))

    assert saved == 3
    assert sorted(b.ticker for b in repo.upserted) == ["AAPL", "AAPL", "NVDA"]
    assert all(call[1] == "5d" for call in fetcher.calls)


def test_individual_fetch_failure_is_graceful_other_tickers_proceed():
    fetcher = _StubFetcher(
        {
            "AAPL": RuntimeError("yfinance 429"),
            "NVDA": [_bar("NVDA", date(2026, 4, 1))],
        }
    )
    repo = _StubRepo()
    usecase = IngestDailyBarsUseCase(fetcher, repo)

    saved = asyncio.run(usecase.execute(tickers=["AAPL", "NVDA"], period="5d"))

    assert saved == 1
    assert [b.ticker for b in repo.upserted] == ["NVDA"]


def test_passes_period_through_to_fetcher():
    fetcher = _StubFetcher({"AAPL": []})
    repo = _StubRepo()
    usecase = IngestDailyBarsUseCase(fetcher, repo)

    asyncio.run(usecase.execute(tickers=["AAPL"], period="max"))

    assert fetcher.calls == [("AAPL", "max")]
