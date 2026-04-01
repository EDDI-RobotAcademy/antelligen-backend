from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_analysis.application.port.out.market_data_port import MarketDataPort
from app.domains.stock_theme.adapter.outbound.persistence.defense_stock_repository_impl import DefenseStockRepositoryImpl
from app.domains.stock_theme.domain.entity.defense_stock import DefenseStock


class MarketDataRepositoryImpl(MarketDataPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def fetch_all_defense_stocks(self) -> list[DefenseStock]:
        repo = DefenseStockRepositoryImpl(self._db)
        return await repo.find_all()
