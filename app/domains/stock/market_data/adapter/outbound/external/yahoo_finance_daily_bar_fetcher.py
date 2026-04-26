import asyncio
import logging
from datetime import date, datetime, timezone
from typing import List, Optional

import yfinance as yf

from app.domains.stock.market_data.application.port.out.daily_bar_fetcher_port import (
    DailyBarFetcherPort,
)
from app.domains.stock.market_data.domain.entity.daily_bar import DailyBar

logger = logging.getLogger(__name__)


class YahooFinanceDailyBarFetcher(DailyBarFetcherPort):
    """yfinance를 통한 일봉 fetch.

    nasdaq_jobs.YahooFinanceNasdaqClient 패턴을 ticker 파라미터화. auto_adjust=True 로
    split/dividend 보정된 close를 close 컬럼에 저장하고, raw close는 adj_close 별도 컬럼.
    """

    async def fetch(
        self,
        ticker: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
        period: Optional[str] = None,
    ) -> List[DailyBar]:
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None, self._fetch_sync, ticker, start, end, period
        )
        if df is None or df.empty:
            logger.warning(
                "[YfinanceDailyBars] 빈 응답: ticker=%s, period=%s, start=%s, end=%s",
                ticker, period, start, end,
            )
            return []
        return self._to_entities(df, ticker)

    def _fetch_sync(
        self,
        ticker: str,
        start: Optional[date],
        end: Optional[date],
        period: Optional[str],
    ):
        t = yf.Ticker(ticker)
        kwargs = {"interval": "1d", "auto_adjust": True}
        if start is not None and end is not None:
            kwargs["start"] = start.isoformat()
            kwargs["end"] = end.isoformat()
        elif period is not None:
            kwargs["period"] = period
        else:
            kwargs["period"] = "5d"

        logger.info(
            "[YfinanceDailyBars] 수집 시작: ticker=%s, %s",
            ticker, {k: v for k, v in kwargs.items() if k != "auto_adjust"},
        )
        return t.history(**kwargs)

    @staticmethod
    def _to_entities(df, ticker: str) -> List[DailyBar]:
        bars: List[DailyBar] = []
        version = f"yfinance:adjusted:{datetime.now(timezone.utc).date().isoformat()}"
        for ts, row in df.iterrows():
            try:
                bar_date = ts.date() if hasattr(ts, "date") else ts
                close_val = float(row["Close"])
                bars.append(
                    DailyBar(
                        ticker=ticker,
                        bar_date=bar_date,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=close_val,
                        volume=int(row.get("Volume", 0) or 0),
                        adj_close=close_val,  # auto_adjust=True 이므로 close 자체가 adjusted
                        source="yfinance",
                        bars_data_version=version,
                    )
                )
            except Exception as e:
                logger.warning(
                    "[YfinanceDailyBars] 행 변환 실패 (ticker=%s, ts=%s): %s",
                    ticker, ts, e,
                )
        logger.info(
            "[YfinanceDailyBars] 수집 완료: ticker=%s, bars=%d",
            ticker, len(bars),
        )
        return bars
