from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class PopularStockTicker:
    ticker: str
    region: str
    asset_type: str
    added_at: datetime
    ticker_id: Optional[int] = None
