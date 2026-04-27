import asyncio
import logging
import os
import threading
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Set

import yfinance as yf

from app.domains.stock.market_data.application.port.out.daily_bar_fetcher_port import (
    DailyBarFetcherPort,
)
from app.domains.stock.market_data.domain.entity.daily_bar import DailyBar

logger = logging.getLogger(__name__)


# KR 종목코드(6자리 숫자) → KOSPI(.KS) / KOSDAQ(.KQ) 변환을 위해 pykrx 의 시장별
# ticker 집합을 프로세스당 1회 조회 후 모듈 캐시. 첫 KR ticker 호출 시 lazy load.
_KR_MARKET_CACHE: Dict[str, Set[str]] = {}
_KR_MARKET_CACHE_LOCK = threading.Lock()


def _set_krx_credentials_from_settings() -> None:
    """pydantic-settings 가 .env 에서 읽은 KRX_ID/KRX_PW 를 os.environ 으로 export.

    pykrx 는 os.environ['KRX_ID'/'KRX_PW'] 만 참조하므로 직접 주입 필요.
    krx_investor_flow_client._set_krx_credentials 와 동일 패턴.
    """
    from app.infrastructure.config.settings import get_settings

    settings = get_settings()
    if settings.krx_id:
        os.environ["KRX_ID"] = settings.krx_id
    if settings.krx_pw:
        os.environ["KRX_PW"] = settings.krx_pw


def _load_kr_markets() -> Dict[str, Set[str]]:
    if _KR_MARKET_CACHE:
        return _KR_MARKET_CACHE
    with _KR_MARKET_CACHE_LOCK:
        if _KR_MARKET_CACHE:
            return _KR_MARKET_CACHE
        try:
            _set_krx_credentials_from_settings()
            from pykrx import stock as krx_stock

            kospi = set(krx_stock.get_market_ticker_list(market="KOSPI"))
            kosdaq = set(krx_stock.get_market_ticker_list(market="KOSDAQ"))
            _KR_MARKET_CACHE["KOSPI"] = kospi
            _KR_MARKET_CACHE["KOSDAQ"] = kosdaq
            logger.info(
                "[YfinanceDailyBars] KR 시장 매핑 캐시 적재: KOSPI=%d, KOSDAQ=%d",
                len(kospi),
                len(kosdaq),
            )
        except Exception as e:
            logger.warning(
                "[YfinanceDailyBars] pykrx KR 시장 조회 실패 — KR ticker 는 .KS fallback: %s",
                e,
            )
            _KR_MARKET_CACHE["KOSPI"] = set()
            _KR_MARKET_CACHE["KOSDAQ"] = set()
    return _KR_MARKET_CACHE


def _to_yahoo_symbol(ticker: str) -> str:
    """DB 표기 ticker → yfinance 가 인식하는 심볼.

    - 6자리 숫자 → pykrx 로 KOSPI(`.KS`) / KOSDAQ(`.KQ`) 자동 결정. 둘 다에 없으면 `.KS` fallback.
    - `^` prefix 또는 이미 `.` 포함 → yfinance native 표기, 그대로 반환.
    - 그 외(US 알파벳 등) → 그대로 반환.
    """
    if not ticker:
        return ticker
    if ticker.startswith("^") or "." in ticker:
        return ticker
    if ticker.isdigit() and len(ticker) == 6:
        markets = _load_kr_markets()
        if ticker in markets.get("KOSDAQ", set()):
            return f"{ticker}.KQ"
        if ticker in markets.get("KOSPI", set()):
            return f"{ticker}.KS"
        logger.warning(
            "[YfinanceDailyBars] KR 시장 미상 ticker — .KS fallback: %s", ticker
        )
        return f"{ticker}.KS"
    return ticker


class YahooFinanceDailyBarFetcher(DailyBarFetcherPort):
    """yfinance를 통한 일봉 fetch.

    nasdaq_jobs.YahooFinanceNasdaqClient 패턴을 ticker 파라미터화. auto_adjust=True 로
    split/dividend 보정된 close를 close 컬럼에 저장하고, raw close는 adj_close 별도 컬럼.

    KR 6자리 종목코드는 yfinance 가 인식하는 `.KS`/`.KQ` 표기로 자동 변환하여 호출하지만,
    저장되는 DailyBar.ticker 는 DB 컨벤션(6자리 raw) 유지.
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
        yahoo_symbol = _to_yahoo_symbol(ticker)
        t = yf.Ticker(yahoo_symbol)
        kwargs = {"interval": "1d", "auto_adjust": True}
        if start is not None and end is not None:
            kwargs["start"] = start.isoformat()
            kwargs["end"] = end.isoformat()
        elif period is not None:
            kwargs["period"] = period
        else:
            kwargs["period"] = "5d"

        log_kwargs = {k: v for k, v in kwargs.items() if k != "auto_adjust"}
        if yahoo_symbol != ticker:
            logger.info(
                "[YfinanceDailyBars] 수집 시작: ticker=%s (yahoo=%s), %s",
                ticker, yahoo_symbol, log_kwargs,
            )
        else:
            logger.info(
                "[YfinanceDailyBars] 수집 시작: ticker=%s, %s",
                ticker, log_kwargs,
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
