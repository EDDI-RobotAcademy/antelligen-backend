"""Yahoo Finance Chart API 기반 투자 정보 조회 어댑터.

FRED 에 없는 지표(예: KOSPI 200) 를 보완한다. API 키 불필요.
"""

import logging
from datetime import datetime, timezone
from typing import Tuple

import httpx

from app.domains.schedule.application.port.out.investment_info_provider_port import (
    InvestmentInfoProviderPort,
)
from app.domains.schedule.domain.entity.investment_info import InvestmentInfo
from app.domains.schedule.domain.value_object.investment_info_type import InvestmentInfoType

logger = logging.getLogger(__name__)

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

# InvestmentInfoType -> (yahoo symbol, unit, description)
_SYMBOL_TABLE: dict[InvestmentInfoType, Tuple[str, str, str]] = {
    InvestmentInfoType.KOSPI_200: (
        "^KS200",
        "index",
        "코스피 200 지수 (KOSPI 200, Daily, Yahoo Finance)",
    ),
    InvestmentInfoType.GOLD: (
        "GC=F",
        "USD/oz",
        "금 선물 근월물 (COMEX Gold Futures, Yahoo Finance)",
    ),
    # 발틱 운임지수(BDI) 는 Baltic Exchange 유료 데이터. BDRY ETF 가 BDI 에 연동된 공개 대리 지표.
    InvestmentInfoType.BALTIC_DRY_INDEX: (
        "BDRY",
        "USD",
        "Breakwave Dry Bulk Shipping ETF — 발틱운임지수(BDI) 연동 대리 지표 "
        "(BDRY, Yahoo Finance)",
    ),
}


class YahooInvestmentInfoClient(InvestmentInfoProviderPort):
    def __init__(self, timeout_seconds: float = 5.0):
        self._timeout = timeout_seconds

    def supports(self, info_type: InvestmentInfoType) -> bool:
        return info_type in _SYMBOL_TABLE

    async def fetch(self, info_type: InvestmentInfoType) -> InvestmentInfo:
        if info_type not in _SYMBOL_TABLE:
            raise ValueError(f"Yahoo 가 지원하지 않는 유형입니다: {info_type}")

        symbol, unit, description = _SYMBOL_TABLE[info_type]
        print(f"[schedule.yahoo] 요청 type={info_type.value} symbol={symbol}")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                YAHOO_CHART_URL.format(symbol=symbol),
                params={"range": "5d", "interval": "1d"},
                headers={"User-Agent": "Mozilla/5.0 (antelligen-backend)"},
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Yahoo Finance 응답 오류 status={response.status_code} "
                f"body={response.text[:200]}"
            )

        data = response.json()
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            err = (data.get("chart") or {}).get("error") or {}
            raise RuntimeError(f"Yahoo 결과 없음 symbol={symbol} error={err}")

        meta = result[0].get("meta") or {}
        price = meta.get("regularMarketPrice")
        if price is None:
            raise RuntimeError(f"regularMarketPrice 누락 symbol={symbol}")

        retrieved_at = datetime.now(timezone.utc)
        print(f"[schedule.yahoo] 응답 symbol={symbol} price={price}")
        return InvestmentInfo(
            info_type=info_type,
            symbol=symbol,
            value=float(price),
            unit=unit,
            retrieved_at=retrieved_at,
            source="Yahoo Finance",
            description=description,
        )
