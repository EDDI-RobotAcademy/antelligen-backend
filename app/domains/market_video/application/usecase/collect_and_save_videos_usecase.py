from app.domains.market_video.application.port.saved_video_repository_port import SavedVideoRepositoryPort
from app.domains.market_video.application.port.youtube_channel_search_port import YoutubeChannelSearchPort
from app.domains.market_video.application.response.collect_videos_response import (
    CollectedVideoItem,
    CollectVideosResponse,
)

DEFENSE_CHANNELS = [
    "UCF8AeLlUbEpKju6v1H6p8Eg",  # 한국경제TV
    "UCbMjg2EvXs_RUGW-KrdM3pw",  # SBS Biz
    "UCTHCOPwqNfZ0uiKOvFyhGwg",  # 연합뉴스TV
    "UCcQTRi69dsVYHN3exePtZ1A",  # KBS News
    "UCG9aFJTZ-lMCHAiO1KJsirg",  # MBN
    "UCsU-I-vHLiaMfV_ceaYz5rQ",  # JTBC News
    "UClErHbdZKUnD1NyIUeQWvuQ",  # 머니투데이
    "UC8Sv6O3Ux8ePVqorx8aOBMg",  # 이데일리TV
    "UCnfwIKyFYRuqZzzKBDt6JOA",  # 매일경제TV
]

DEFENSE_KEYWORDS = [
    "전쟁", "군사", "미사일", "방위산업", "무기", "NATO", "국방", "방산",
    "전투기", "잠수함", "군함", "육군", "해군", "공군", "방공", "탄도",
    "로켓", "포탄", "장갑차", "전차", "핵", "K방산", "나토", "드론",
]

TOP_N = 10
MAX_RESULTS_PER_CHANNEL = 10
MIN_KEYWORD_COUNT = 1


class CollectAndSaveVideosUseCase:
    def __init__(
        self,
        channel_search_port: YoutubeChannelSearchPort,
        repository: SavedVideoRepositoryPort,
    ):
        self._channel_search_port = channel_search_port
        self._repository = repository

    async def execute(self, recent_days: int = 7) -> CollectVideosResponse:
        if not DEFENSE_CHANNELS:
            return CollectVideosResponse(saved_count=0, videos=[])

        all_videos = await self._channel_search_port.search_by_channels(
            channel_ids=DEFENSE_CHANNELS,
            recent_days=recent_days,
            max_results_per_channel=MAX_RESULTS_PER_CHANNEL,
        )

        filtered = [v for v in all_videos if self._passes_keyword_filter(v.title)]

        sorted_videos = sorted(filtered, key=lambda v: v.published_at, reverse=True)

        top_videos = sorted_videos[:TOP_N]

        if not top_videos:
            return CollectVideosResponse(saved_count=0, videos=[])

        saved = []
        for video in top_videos:
            try:
                saved_video = await self._repository.upsert(video)
                saved.append(saved_video)
            except Exception:
                continue

        items = [
            CollectedVideoItem(
                video_id=v.video_id,
                title=v.title,
                channel_name=v.channel_name,
                published_at=v.published_at,
                view_count=v.view_count,
                thumbnail_url=v.thumbnail_url,
                video_url=v.video_url,
            )
            for v in saved
        ]
        return CollectVideosResponse(saved_count=len(items), videos=items)

    @staticmethod
    def _passes_keyword_filter(title: str) -> bool:
        matched = sum(1 for kw in DEFENSE_KEYWORDS if kw.lower() in title.lower())
        return matched >= MIN_KEYWORD_COUNT
