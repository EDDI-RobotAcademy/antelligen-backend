from abc import ABC, abstractmethod

from app.domains.market_video.domain.entity.saved_youtube_video import SavedYoutubeVideo


class YoutubeChannelSearchPort(ABC):

    @abstractmethod
    async def search_by_channels(
        self,
        channel_ids: list[str],
        recent_days: int,
        max_results_per_channel: int,
    ) -> list[SavedYoutubeVideo]:
        """채널 목록에서 최근 N일 이내 영상을 조회하여 반환"""
        pass
