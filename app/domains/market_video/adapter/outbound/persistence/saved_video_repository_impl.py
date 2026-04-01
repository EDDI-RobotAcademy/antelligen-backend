from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_video.application.port.saved_video_repository_port import SavedVideoRepositoryPort
from app.domains.market_video.domain.entity.saved_youtube_video import SavedYoutubeVideo
from app.domains.market_video.infrastructure.mapper.saved_youtube_video_mapper import SavedYoutubeVideoMapper
from app.domains.market_video.infrastructure.orm.saved_youtube_video_orm import SavedYoutubeVideoOrm


class SavedVideoRepositoryImpl(SavedVideoRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def upsert(self, video: SavedYoutubeVideo) -> SavedYoutubeVideo:
        result = await self._db.execute(
            select(SavedYoutubeVideoOrm).where(SavedYoutubeVideoOrm.video_id == video.video_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.title = video.title
            existing.channel_name = video.channel_name
            existing.published_at = video.published_at
            existing.view_count = video.view_count
            existing.thumbnail_url = video.thumbnail_url
            existing.video_url = video.video_url
            await self._db.flush()
            await self._db.commit()
            return SavedYoutubeVideoMapper.to_entity(existing)

        orm = SavedYoutubeVideoMapper.to_orm(video)
        self._db.add(orm)
        await self._db.flush()
        await self._db.commit()
        await self._db.refresh(orm)
        return SavedYoutubeVideoMapper.to_entity(orm)

    async def find_page(
        self, page: int, page_size: int
    ) -> tuple[list[SavedYoutubeVideo], int]:
        offset = (page - 1) * page_size

        total_result = await self._db.execute(
            select(func.count()).select_from(SavedYoutubeVideoOrm)
        )
        total = total_result.scalar_one()

        rows = await self._db.execute(
            select(SavedYoutubeVideoOrm)
            .order_by(SavedYoutubeVideoOrm.published_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        entities = [SavedYoutubeVideoMapper.to_entity(row) for row in rows.scalars().all()]
        return entities, total
