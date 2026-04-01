from abc import ABC, abstractmethod

from app.domains.market_video.domain.entity.saved_youtube_video import SavedYoutubeVideo


class SavedVideoRepositoryPort(ABC):

    @abstractmethod
    async def upsert(self, video: SavedYoutubeVideo) -> SavedYoutubeVideo:
        """video_id 기준으로 존재하면 갱신, 없으면 신규 저장"""
        pass

    @abstractmethod
    async def find_page(
        self, page: int, page_size: int
    ) -> tuple[list[SavedYoutubeVideo], int]:
        """게시일 내림차순으로 페이지 조회. (videos, total_count) 반환"""
        pass
