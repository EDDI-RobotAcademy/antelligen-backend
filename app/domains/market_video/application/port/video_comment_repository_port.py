from abc import ABC, abstractmethod
from typing import List, Set

from app.domains.market_video.domain.entity.video_comment import VideoComment


class VideoCommentRepositoryPort(ABC):
    @abstractmethod
    async def find_by_video_id(self, video_id: str) -> List[VideoComment]:
        pass

    @abstractmethod
    async def find_all(self) -> List[VideoComment]:
        pass

    @abstractmethod
    async def save(self, comment: VideoComment) -> VideoComment:
        pass

    @abstractmethod
    async def find_existing_youtube_comment_ids(self, youtube_comment_ids: List[str]) -> Set[str]:
        """주어진 youtube_comment_id 중 이미 DB에 저장된 것들을 반환한다."""
        pass
