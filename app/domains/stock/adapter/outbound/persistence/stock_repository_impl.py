import csv
from pathlib import Path
from typing import Optional

from app.domains.stock.application.port.stock_repository import StockRepository
from app.domains.stock.domain.entity.stock import Stock

CSV_PATH = Path(__file__).resolve().parents[3] / "infrastructure" / "data" / "stocks.csv"


class StockRepositoryImpl(StockRepository):

    async def find_by_ticker(self, ticker: str) -> Optional[Stock]:
        with open(CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["ticker"] == ticker:
                    return Stock(
                        ticker=row["ticker"],
                        stock_name=row["stock_name"],
                        market=row["market"],
                    )
        return None

    async def find_by_company_name(self, company_name: str) -> Optional[Stock]:
        normalized_query = self._normalize(company_name)

        with open(CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self._normalize(row["stock_name"]) == normalized_query:
                    return Stock(
                        ticker=row["ticker"],
                        stock_name=row["stock_name"],
                        market=row["market"],
                    )
        return None

    def _normalize(self, value: str) -> str:
        return "".join(value.strip().lower().split())
