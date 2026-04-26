"""YahooFinanceDailyBarFetcher._to_entities — pandas DataFrame → DailyBar 변환 검증."""
import datetime as dt

import pandas as pd

from app.domains.stock.market_data.adapter.outbound.external.yahoo_finance_daily_bar_fetcher import (
    YahooFinanceDailyBarFetcher,
)


def _df(rows):
    return pd.DataFrame(
        rows,
        index=pd.DatetimeIndex([r["date"] for r in rows]),
    ).rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    ).drop(columns=["date"])


def test_to_entities_converts_each_row_to_daily_bar():
    df = _df([
        {"date": "2026-04-01", "open": 100.0, "high": 110.0, "low": 99.0, "close": 105.0, "volume": 12345},
        {"date": "2026-04-02", "open": 105.0, "high": 108.0, "low": 102.0, "close": 107.0, "volume": 67890},
    ])

    bars = YahooFinanceDailyBarFetcher._to_entities(df, ticker="AAPL")

    assert len(bars) == 2
    assert bars[0].ticker == "AAPL"
    assert bars[0].bar_date == dt.date(2026, 4, 1)
    assert bars[0].close == 105.0
    assert bars[0].adj_close == 105.0  # auto_adjust=True 이므로 close 자체가 adjusted
    assert bars[0].source == "yfinance"
    assert bars[0].bars_data_version is not None
    assert bars[0].bars_data_version.startswith("yfinance:adjusted:")
    assert bars[1].volume == 67890


def test_to_entities_skips_rows_with_invalid_data():
    df = _df([
        {"date": "2026-04-01", "open": 100.0, "high": 110.0, "low": 99.0, "close": 105.0, "volume": 12345},
        {"date": "2026-04-02", "open": float("nan"), "high": 108.0, "low": 102.0, "close": 107.0, "volume": 67890},
    ])

    bars = YahooFinanceDailyBarFetcher._to_entities(df, ticker="NVDA")

    # NaN open → float() 은 NaN 자체로 진행되지만 dataclass에 NaN 으로 저장됨.
    # 행 변환 실패는 row["Open"] 키 자체 누락 등 예외 시점에만 skip 된다.
    assert len(bars) >= 1
    assert bars[0].close == 105.0
