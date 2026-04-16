from abc import ABC, abstractmethod
from typing import Optional

from app.domains.market_video.domain.entity.youtube_video import YoutubeVideo


class YoutubeSearchPort(ABC):
    @abstractmethod
    async def search(
        self,
        page_token: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> tuple[list[YoutubeVideo], Optional[str], Optional[str], int]:
        """
        Args:
            page_token: 페이지네이션 토큰
            keyword: 검색 키워드. None이면 클라이언트 기본값(하드코딩) 사용.

        Returns: (videos, next_page_token, prev_page_token, total_results)
        """
        pass
