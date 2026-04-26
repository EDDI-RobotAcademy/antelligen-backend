from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class DailyBar:
    ticker: str
    bar_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None
    source: str = "yfinance"
    bars_data_version: Optional[str] = None
