from typing import List

from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.account.infrastructure.orm.user_watchlist_orm import UserWatchlistOrm
from app.domains.stock.market_data.application.port.out.watchlist_ticker_query_port import (
    WatchlistTickerQueryPort,
)


class WatchlistTickerQueryImpl(WatchlistTickerQueryPort):

    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_distinct_tickers(self) -> List[str]:
        stmt = select(distinct(UserWatchlistOrm.stock_code)).order_by(
            UserWatchlistOrm.stock_code
        )
        result = await self._db.execute(stmt)
        return [row[0] for row in result.all() if row[0]]
