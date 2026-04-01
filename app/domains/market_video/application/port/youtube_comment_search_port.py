from abc import ABC, abstractmethod
from typing import List

from app.domains.market_video.domain.entity.video_comment import VideoComment


class YoutubeCommentSearchPort(ABC):
    @abstractmethod
    async def fetch_comments(
        self,
        video_id: str,
        max_count: int,
        order: str,
    ) -> List[VideoComment]:
        """YouTube 영상의 댓글을 수집한다.

        Args:
            video_id: YouTube 영상 ID
            max_count: 최대 수집 댓글 수
            order: 정렬 기준 ("time" | "relevance")

        Returns:
            댓글이 비활성화되었거나 영상이 없으면 빈 리스트 반환
        """
        pass
