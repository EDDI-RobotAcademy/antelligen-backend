from app.domains.stock_theme.application.port.defense_stock_repository_port import DefenseStockRepositoryPort
from app.domains.stock_theme.domain.entity.defense_stock import DefenseStock
from app.domains.stock_theme.domain.service.defense_stock_seed_data import DEFENSE_STOCK_SEED


class SeedDefenseStocksUseCase:
    """앱 시작 시 방산주 사전 데이터를 DB에 등록한다."""

    def __init__(self, repository: DefenseStockRepositoryPort):
        self._repository = repository

    async def execute(self) -> int:
        """시드 데이터를 upsert하고 처리된 종목 수를 반환한다."""
        count = 0
        for data in DEFENSE_STOCK_SEED:
            stock = DefenseStock(
                name=data["name"],
                code=data["code"],
                themes=data["themes"],
            )
            await self._repository.upsert(stock)
            count += 1
        return count
