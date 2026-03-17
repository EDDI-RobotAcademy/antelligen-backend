import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news.application.port.saved_article_repository import (
    SavedArticleRepository,
)
from app.domains.news.domain.entity.saved_article import SavedArticle
from app.domains.news.infrastructure.mapper.saved_article_mapper import (
    SavedArticleMapper,
)
from app.domains.news.infrastructure.orm.saved_article_orm import SavedArticleOrm


class SavedArticleRepositoryImpl(SavedArticleRepository):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def save(self, article: SavedArticle) -> SavedArticle:
        orm = SavedArticleMapper.to_orm(article)
        self._db.add(orm)
        await self._db.commit()
        await self._db.refresh(orm)
        return SavedArticleMapper.to_entity(orm)

    async def find_by_id(self, article_id: int) -> SavedArticle | None:
        stmt = select(SavedArticleOrm).where(SavedArticleOrm.id == article_id)
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return SavedArticleMapper.to_entity(orm)

    async def find_by_link(self, link: str) -> SavedArticle | None:
        link_hash = hashlib.sha256(link.encode()).hexdigest()
        stmt = select(SavedArticleOrm).where(SavedArticleOrm.link_hash == link_hash)
        result = await self._db.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return SavedArticleMapper.to_entity(orm)
