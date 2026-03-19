from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.account.application.port.out.account_repository_port import AccountRepositoryPort
from app.domains.account.domain.entity.account import Account
from app.domains.account.infrastructure.mapper.account_mapper import AccountMapper
from app.domains.account.infrastructure.orm.account_orm import AccountOrm


class AccountRepositoryImpl(AccountRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_email(self, email: str) -> Optional[Account]:
        stmt = select(AccountOrm).where(AccountOrm.email == email)
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return AccountMapper.to_entity(orm)
