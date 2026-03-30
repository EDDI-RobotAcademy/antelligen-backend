from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FinancialRatio:
    """재무비율 도메인 엔티티"""
    ticker: str
    corp_code: str
    fiscal_year: str
    roe: Optional[float] = None  # 자기자본이익률 (%)
    roa: Optional[float] = None  # 총자산이익률 (%)
    per: Optional[float] = None  # 주가수익비율 (배)
    pbr: Optional[float] = None  # 주가순자산비율 (배)
    debt_ratio: Optional[float] = None  # 부채비율 (%)
    collected_at: Optional[datetime] = None
