"""종목 일봉 OHLCV 적재 잡 (PR1).

`nasdaq_jobs.py` 를 ticker-축으로 일반화. popular_stock_tickers seed + user_watchlist
distinct ticker 합집합을 대상으로 부트스트랩(period="max") + 일별 증분(period="5d").
"""
import logging
import time
from typing import List

from app.infrastructure.database.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def _collect_target_tickers() -> List[str]:
    """popular_stock_tickers ∪ user_watchlist distinct stock_code."""
    from app.domains.stock.market_data.adapter.outbound.persistence.popular_stock_ticker_repository_impl import (
        PopularStockTickerRepositoryImpl,
    )
    from app.domains.stock.market_data.adapter.outbound.persistence.watchlist_ticker_query_impl import (
        WatchlistTickerQueryImpl,
    )

    async with AsyncSessionLocal() as db:
        popular = await PopularStockTickerRepositoryImpl(db).find_all()
        watchlist = await WatchlistTickerQueryImpl(db).find_distinct_tickers()

    pool = {p.ticker for p in popular} | set(watchlist)
    return sorted(pool)


async def job_bootstrap_stock_bars():
    """서버 시작 시 1회 실행 — daily_bars에 한 번도 적재된 적 없는 ticker만 period="max" 백필.

    이미 적재된 ticker는 skip (job_collect_stock_bars_daily 가 누락 보완 담당).
    """
    from app.domains.stock.market_data.adapter.outbound.external.yahoo_finance_daily_bar_fetcher import (
        YahooFinanceDailyBarFetcher,
    )
    from app.domains.stock.market_data.adapter.outbound.persistence.daily_bar_repository_impl import (
        DailyBarRepositoryImpl,
    )
    from app.domains.stock.market_data.application.usecase.ingest_daily_bars_usecase import (
        IngestDailyBarsUseCase,
    )

    start = time.monotonic()
    logger.info("[Bootstrap][StockBars] 적재 대상 ticker 조회 중...")
    tickers = await _collect_target_tickers()
    if not tickers:
        logger.info("[Bootstrap][StockBars] 대상 ticker 없음 — skip")
        return

    fetcher = YahooFinanceDailyBarFetcher()
    pending: List[str] = []
    async with AsyncSessionLocal() as db:
        repo = DailyBarRepositoryImpl(db)
        for t in tickers:
            latest = await repo.find_latest_bar_date(t)
            if latest is None:
                pending.append(t)

    if not pending:
        logger.info(
            "[Bootstrap][StockBars] 모든 ticker 적재 완료 상태 — skip (total=%d)",
            len(tickers),
        )
        return

    logger.info(
        "[Bootstrap][StockBars] 미적재 ticker %d/%d 백필 시작 (period=max)",
        len(pending), len(tickers),
    )
    async with AsyncSessionLocal() as db:
        usecase = IngestDailyBarsUseCase(
            fetcher=fetcher,
            repository=DailyBarRepositoryImpl(db),
        )
        saved = await usecase.execute(tickers=pending, period="max", concurrency=2)

    elapsed = time.monotonic() - start
    logger.info(
        "[Bootstrap][StockBars] 완료 — pending=%d saved=%d (%.1fs)",
        len(pending), saved, elapsed,
    )


async def job_collect_stock_bars_daily():
    """Daily KST 07:30 — daily_bars 의 모든 distinct ticker에 대해 period="5d" 재조회.

    누락·재처리 보완. corporate action(split) 발생 시 `auto_adjust=True` 로 인해
    자동으로 adjusted close 가 갱신된다 (bars_data_version 도 새 날짜로 갱신).
    """
    from app.domains.stock.market_data.adapter.outbound.external.yahoo_finance_daily_bar_fetcher import (
        YahooFinanceDailyBarFetcher,
    )
    from app.domains.stock.market_data.adapter.outbound.persistence.daily_bar_repository_impl import (
        DailyBarRepositoryImpl,
    )
    from app.domains.stock.market_data.application.usecase.ingest_daily_bars_usecase import (
        IngestDailyBarsUseCase,
    )

    start = time.monotonic()
    logger.info("[Scheduler][CollectStockBars] 일별 증분 수집 시작 (period=5d)")
    try:
        async with AsyncSessionLocal() as db:
            tickers = await DailyBarRepositoryImpl(db).find_distinct_tickers()
        if not tickers:
            logger.info("[Scheduler][CollectStockBars] 적재된 ticker 없음 — skip")
            return

        async with AsyncSessionLocal() as db:
            usecase = IngestDailyBarsUseCase(
                fetcher=YahooFinanceDailyBarFetcher(),
                repository=DailyBarRepositoryImpl(db),
            )
            saved = await usecase.execute(tickers=tickers, period="5d", concurrency=4)
        elapsed = time.monotonic() - start
        logger.info(
            "[Scheduler][CollectStockBars] 완료 — tickers=%d saved=%d (%.1fs)",
            len(tickers), saved, elapsed,
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error(
            "[Scheduler][CollectStockBars] 실패 (%.1fs): %s", elapsed, e
        )


async def job_backfill_new_tickers():
    """Hourly — 미적재 ticker(watchlist 신규 추가 등)에 대해 period="max" lazy 백필.

    bootstrap 이후 운영 중 사용자가 watchlist에 신규 추가한 종목을 자동 적재.
    """
    from app.domains.stock.market_data.adapter.outbound.external.yahoo_finance_daily_bar_fetcher import (
        YahooFinanceDailyBarFetcher,
    )
    from app.domains.stock.market_data.adapter.outbound.persistence.daily_bar_repository_impl import (
        DailyBarRepositoryImpl,
    )
    from app.domains.stock.market_data.application.usecase.ingest_daily_bars_usecase import (
        IngestDailyBarsUseCase,
    )

    start = time.monotonic()
    tickers = await _collect_target_tickers()
    if not tickers:
        return

    pending: List[str] = []
    async with AsyncSessionLocal() as db:
        repo = DailyBarRepositoryImpl(db)
        for t in tickers:
            if await repo.find_latest_bar_date(t) is None:
                pending.append(t)
    if not pending:
        return

    logger.info(
        "[Scheduler][BackfillNewTickers] 신규 ticker 발견 %d건 — period=max 백필",
        len(pending),
    )
    try:
        async with AsyncSessionLocal() as db:
            usecase = IngestDailyBarsUseCase(
                fetcher=YahooFinanceDailyBarFetcher(),
                repository=DailyBarRepositoryImpl(db),
            )
            saved = await usecase.execute(tickers=pending, period="max", concurrency=2)
        elapsed = time.monotonic() - start
        logger.info(
            "[Scheduler][BackfillNewTickers] 완료 — pending=%d saved=%d (%.1fs)",
            len(pending), saved, elapsed,
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error(
            "[Scheduler][BackfillNewTickers] 실패 (%.1fs): %s", elapsed, e
        )
