from typing import Optional

from app.domains.stock.application.port.stock_repository import StockRepository
from app.domains.stock.application.response.stock_response import StockResponse


class GetStockUseCase:
    def __init__(self, stock_repository: StockRepository):
        self._stock_repository = stock_repository

    async def execute(self, ticker: str) -> Optional[StockResponse]:
        stock = await self._stock_repository.find_by_ticker(ticker)
        if stock is None:
            return None

        return StockResponse(
            ticker=stock.ticker,
            stock_name=stock.stock_name,
            market=stock.market,
        )
