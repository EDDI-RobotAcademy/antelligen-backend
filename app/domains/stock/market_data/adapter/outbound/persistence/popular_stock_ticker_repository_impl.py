import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.stock.market_data.application.port.out.popular_stock_ticker_repository_port import (
    PopularStockTickerRepositoryPort,
)
from app.domains.stock.market_data.domain.entity.popular_stock_ticker import (
    PopularStockTicker,
)
from app.domains.stock.market_data.infrastructure.mapper.popular_stock_ticker_mapper import (
    PopularStockTickerMapper,
)
from app.domains.stock.market_data.infrastructure.orm.popular_stock_ticker_orm import (
    PopularStockTickerOrm,
)

logger = logging.getLogger(__name__)


class PopularStockTickerRepositoryImpl(PopularStockTickerRepositoryPort):

    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_all(self) -> List[PopularStockTicker]:
        stmt = select(PopularStockTickerOrm).order_by(PopularStockTickerOrm.added_at)
        result = await self._db.execute(stmt)
        return [
            PopularStockTickerMapper.to_entity(orm)
            for orm in result.scalars().all()
        ]

    async def find_by_region(self, region: str) -> List[PopularStockTicker]:
        stmt = (
            select(PopularStockTickerOrm)
            .where(PopularStockTickerOrm.region == region)
            .order_by(PopularStockTickerOrm.added_at)
        )
        result = await self._db.execute(stmt)
        return [
            PopularStockTickerMapper.to_entity(orm)
            for orm in result.scalars().all()
        ]
