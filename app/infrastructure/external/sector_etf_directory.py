"""
미국 인기 종목 → SPDR 섹터 ETF 매핑 (GICS 11 섹터).

`korean_company_directory` 와 동일 위치. ticker 가 매핑에 없으면 None — sector 비교 미수행.
한국 종목은 본 매핑 대상 외(향후 KODEX 섹터 ETF 별도).

| ETF | GICS Sector |
|-----|-------------|
| XLK | Technology |
| XLV | Health Care |
| XLF | Financials |
| XLY | Consumer Discretionary |
| XLP | Consumer Staples |
| XLE | Energy |
| XLI | Industrials |
| XLB | Materials |
| XLU | Utilities |
| XLRE | Real Estate |
| XLC | Communication Services |
"""

from typing import Optional


_SECTOR_ETF_NAMES: dict[str, str] = {
    "XLK": "Technology Sector SPDR",
    "XLV": "Health Care Sector SPDR",
    "XLF": "Financials Sector SPDR",
    "XLY": "Consumer Discretionary Sector SPDR",
    "XLP": "Consumer Staples Sector SPDR",
    "XLE": "Energy Sector SPDR",
    "XLI": "Industrials Sector SPDR",
    "XLB": "Materials Sector SPDR",
    "XLU": "Utilities Sector SPDR",
    "XLRE": "Real Estate Sector SPDR",
    "XLC": "Communication Services Sector SPDR",
}

# 인기 종목 + GICS 매핑. 점진 확장 — DART 의 corp_code 처럼 DB 화 가능하나 정적이면 충분.
_TICKER_TO_SECTOR: dict[str, str] = {
    # Technology (XLK)
    "AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AVGO": "XLK", "ORCL": "XLK",
    "CRM": "XLK", "ADBE": "XLK", "AMD": "XLK", "INTC": "XLK", "QCOM": "XLK",
    "CSCO": "XLK", "IBM": "XLK", "TXN": "XLK", "AMAT": "XLK", "MU": "XLK",
    "NOW": "XLK", "INTU": "XLK", "PANW": "XLK", "SNPS": "XLK", "CDNS": "XLK",

    # Communication Services (XLC)
    "GOOGL": "XLC", "GOOG": "XLC", "META": "XLC", "NFLX": "XLC", "DIS": "XLC",
    "TMUS": "XLC", "VZ": "XLC", "T": "XLC", "CMCSA": "XLC", "EA": "XLC",

    # Consumer Discretionary (XLY)
    "AMZN": "XLY", "TSLA": "XLY", "HD": "XLY", "MCD": "XLY", "NKE": "XLY",
    "SBUX": "XLY", "BKNG": "XLY", "LOW": "XLY", "TJX": "XLY", "ABNB": "XLY",

    # Consumer Staples (XLP)
    "WMT": "XLP", "PG": "XLP", "COST": "XLP", "KO": "XLP", "PEP": "XLP",
    "PM": "XLP", "MO": "XLP", "MDLZ": "XLP", "CL": "XLP",

    # Health Care (XLV)
    "UNH": "XLV", "JNJ": "XLV", "LLY": "XLV", "PFE": "XLV", "MRK": "XLV",
    "ABBV": "XLV", "TMO": "XLV", "ABT": "XLV", "DHR": "XLV", "BMY": "XLV",
    "AMGN": "XLV", "GILD": "XLV", "CVS": "XLV",

    # Financials (XLF)
    "BRK-B": "XLF", "JPM": "XLF", "V": "XLF", "MA": "XLF", "BAC": "XLF",
    "WFC": "XLF", "GS": "XLF", "MS": "XLF", "AXP": "XLF", "C": "XLF",
    "BLK": "XLF", "SCHW": "XLF",

    # Energy (XLE)
    "XOM": "XLE", "CVX": "XLE", "COP": "XLE", "SLB": "XLE", "EOG": "XLE",
    "MPC": "XLE", "PSX": "XLE", "OXY": "XLE",

    # Industrials (XLI)
    "BA": "XLI", "CAT": "XLI", "HON": "XLI", "UNP": "XLI", "GE": "XLI",
    "RTX": "XLI", "LMT": "XLI", "DE": "XLI", "UPS": "XLI",

    # Materials (XLB)
    "LIN": "XLB", "FCX": "XLB", "NEM": "XLB", "DOW": "XLB",

    # Utilities (XLU)
    "NEE": "XLU", "SO": "XLU", "DUK": "XLU", "AEP": "XLU",

    # Real Estate (XLRE)
    "PLD": "XLRE", "AMT": "XLRE", "EQIX": "XLRE", "SPG": "XLRE",
}


def lookup_sector_etf(ticker: str) -> Optional[tuple[str, str]]:
    """ticker → (etf_symbol, etf_name). 매핑 없으면 None.

    대문자/소문자 무관. 한국 종목·지수·기타 ticker 는 일관되게 None.
    """
    if not ticker:
        return None
    upper = ticker.upper()
    etf = _TICKER_TO_SECTOR.get(upper)
    if etf is None:
        return None
    return etf, _SECTOR_ETF_NAMES.get(etf, etf)
