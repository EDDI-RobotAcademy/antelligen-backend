import logging
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import distinct, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.stock.market_data.application.port.out.daily_bar_repository_port import (
    DailyBarRepositoryPort,
)
from app.domains.stock.market_data.domain.entity.daily_bar import DailyBar
from app.domains.stock.market_data.infrastructure.mapper.daily_bar_mapper import (
    DailyBarMapper,
)
from app.domains.stock.market_data.infrastructure.orm.daily_bar_orm import DailyBarOrm

logger = logging.getLogger(__name__)

# asyncpg 파라미터 한계(32767). 컬럼 11개 기준 안전선.
_CHUNK_SIZE = 2500


class DailyBarRepositoryImpl(DailyBarRepositoryPort):

    def __init__(self, db: AsyncSession):
        self._db = db

    async def upsert_bulk(self, bars: List[DailyBar]) -> int:
        if not bars:
            return 0

        total = 0
        for i in range(0, len(bars), _CHUNK_SIZE):
            chunk = bars[i : i + _CHUNK_SIZE]
            values = [
                {
                    "ticker": bar.ticker,
                    "bar_date": bar.bar_date,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": int(bar.volume),
                    "adj_close": bar.adj_close,
                    "source": bar.source,
                    "bars_data_version": bar.bars_data_version,
                }
                for bar in chunk
            ]
            insert_stmt = pg_insert(DailyBarOrm).values(values)
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=["ticker", "bar_date"],
                set_={
                    "open": insert_stmt.excluded.open,
                    "high": insert_stmt.excluded.high,
                    "low": insert_stmt.excluded.low,
                    "close": insert_stmt.excluded.close,
                    "volume": insert_stmt.excluded.volume,
                    "adj_close": insert_stmt.excluded.adj_close,
                    "source": insert_stmt.excluded.source,
                    "bars_data_version": insert_stmt.excluded.bars_data_version,
                },
            ).returning(DailyBarOrm.id)
            result = await self._db.execute(upsert_stmt)
            total += len(result.fetchall())

        await self._db.commit()
        logger.info("[DailyBarRepository] upsert 완료: %d rows", total)
        return total

    async def find_range(
        self, ticker: str, start: date, end: date
    ) -> List[DailyBar]:
        stmt = (
            select(DailyBarOrm)
            .where(
                DailyBarOrm.ticker == ticker,
                DailyBarOrm.bar_date >= start,
                DailyBarOrm.bar_date <= end,
            )
            .order_by(DailyBarOrm.bar_date.asc())
        )
        result = await self._db.execute(stmt)
        return [DailyBarMapper.to_entity(orm) for orm in result.scalars().all()]

    async def find_around(
        self,
        ticker: str,
        event_date: date,
        before_days: int,
        after_days: int,
    ) -> List[DailyBar]:
        # 캘린더 기준 ±N일로 잡고 호출자가 거래일 슬라이싱.
        # 거래일 환산 시 주말/공휴일 손실을 보정하기 위해 약간 여유롭게 가져온다.
        padding = max(7, (before_days + after_days) // 4)
        start = event_date - timedelta(days=before_days + padding)
        end = event_date + timedelta(days=after_days + padding)
        return await self.find_range(ticker, start, end)

    async def find_latest_bar_date(self, ticker: str) -> Optional[date]:
        stmt = select(func.max(DailyBarOrm.bar_date)).where(
            DailyBarOrm.ticker == ticker
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_distinct_tickers(self) -> List[str]:
        stmt = select(distinct(DailyBarOrm.ticker)).order_by(DailyBarOrm.ticker)
        result = await self._db.execute(stmt)
        return [row[0] for row in result.all()]
