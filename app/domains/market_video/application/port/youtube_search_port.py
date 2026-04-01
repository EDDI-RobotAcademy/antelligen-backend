from abc import ABC, abstractmethod
from typing import Optional

from app.domains.market_video.domain.entity.youtube_video import YoutubeVideo


class YoutubeSearchPort(ABC):
    @abstractmethod
    async def search(
        self,
        page_token: Optional[str] = None,
    ) -> tuple[list[YoutubeVideo], Optional[str], Optional[str], int]:
        """
        Returns: (videos, next_page_token, prev_page_token, total_results)
        """
        pass
