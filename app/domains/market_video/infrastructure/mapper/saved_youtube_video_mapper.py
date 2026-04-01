from app.domains.market_video.domain.entity.saved_youtube_video import SavedYoutubeVideo
from app.domains.market_video.infrastructure.orm.saved_youtube_video_orm import SavedYoutubeVideoOrm


class SavedYoutubeVideoMapper:

    @staticmethod
    def to_orm(video: SavedYoutubeVideo) -> SavedYoutubeVideoOrm:
        return SavedYoutubeVideoOrm(
            video_id=video.video_id,
            title=video.title,
            channel_name=video.channel_name,
            published_at=video.published_at,
            view_count=video.view_count,
            thumbnail_url=video.thumbnail_url,
            video_url=video.video_url,
        )

    @staticmethod
    def to_entity(orm: SavedYoutubeVideoOrm) -> SavedYoutubeVideo:
        return SavedYoutubeVideo(
            db_id=orm.id,
            video_id=orm.video_id,
            title=orm.title,
            channel_name=orm.channel_name,
            published_at=orm.published_at,
            view_count=orm.view_count,
            thumbnail_url=orm.thumbnail_url,
            video_url=orm.video_url,
        )
