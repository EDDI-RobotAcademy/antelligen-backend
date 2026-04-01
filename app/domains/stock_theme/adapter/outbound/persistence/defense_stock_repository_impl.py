from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.stock_theme.application.port.defense_stock_repository_port import DefenseStockRepositoryPort
from app.domains.stock_theme.domain.entity.defense_stock import DefenseStock
from app.domains.stock_theme.infrastructure.mapper.defense_stock_mapper import DefenseStockMapper
from app.domains.stock_theme.infrastructure.orm.defense_stock_orm import DefenseStockOrm


class DefenseStockRepositoryImpl(DefenseStockRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def upsert(self, stock: DefenseStock) -> DefenseStock:
        result = await self._db.execute(
            select(DefenseStockOrm).where(DefenseStockOrm.code == stock.code)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = stock.name
            existing.themes = stock.themes
            await self._db.flush()
            await self._db.commit()
            return DefenseStockMapper.to_entity(existing)

        orm = DefenseStockMapper.to_orm(stock)
        self._db.add(orm)
        await self._db.flush()
        await self._db.commit()
        await self._db.refresh(orm)
        return DefenseStockMapper.to_entity(orm)

    async def find_all(self) -> list[DefenseStock]:
        result = await self._db.execute(
            select(DefenseStockOrm).order_by(DefenseStockOrm.name)
        )
        return [DefenseStockMapper.to_entity(row) for row in result.scalars().all()]

    async def find_by_theme(self, theme: str) -> list[DefenseStock]:
        """JSON 컬럼에서 테마 키워드가 포함된 종목을 필터링한다."""
        result = await self._db.execute(
            select(DefenseStockOrm).order_by(DefenseStockOrm.name)
        )
        all_stocks = result.scalars().all()
        matched = [orm for orm in all_stocks if theme in (orm.themes or [])]
        return [DefenseStockMapper.to_entity(orm) for orm in matched]

    async def find_by_code(self, code: str) -> Optional[DefenseStock]:
        result = await self._db.execute(
            select(DefenseStockOrm).where(DefenseStockOrm.code == code)
        )
        orm = result.scalar_one_or_none()
        return DefenseStockMapper.to_entity(orm) if orm else None
