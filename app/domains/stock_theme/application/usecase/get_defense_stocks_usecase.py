from typing import Optional

from app.domains.stock_theme.application.port.defense_stock_repository_port import DefenseStockRepositoryPort
from app.domains.stock_theme.application.response.defense_stock_response import DefenseStockItem, DefenseStockListResponse


class GetDefenseStocksUseCase:
    def __init__(self, repository: DefenseStockRepositoryPort):
        self._repository = repository

    async def execute(self, theme: Optional[str] = None) -> DefenseStockListResponse:
        if theme:
            stocks = await self._repository.find_by_theme(theme)
        else:
            stocks = await self._repository.find_all()

        items = [
            DefenseStockItem(
                id=stock.db_id,
                name=stock.name,
                code=stock.code,
                themes=stock.themes,
            )
            for stock in stocks
        ]
        return DefenseStockListResponse(total=len(items), items=items)
