from typing import Optional

import httpx

from app.domains.market_video.application.port.youtube_search_port import YoutubeSearchPort
from app.domains.market_video.domain.entity.youtube_video import YoutubeVideo

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
SEARCH_KEYWORD = "방산주 방위산업 한국 주식"
PAGE_SIZE = 9


class YoutubeSearchClient(YoutubeSearchPort):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(
        self,
        page_token: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> tuple[list[YoutubeVideo], Optional[str], Optional[str], int]:
        effective_keyword = keyword if keyword else SEARCH_KEYWORD
        params = {
            "key": self._api_key,
            "q": effective_keyword,
            "part": "snippet",
            "type": "video",
            "maxResults": PAGE_SIZE,
            "relevanceLanguage": "ko",
            "order": "date",
        }
        if page_token:
            params["pageToken"] = page_token

        async with httpx.AsyncClient() as client:
            response = await client.get(YOUTUBE_SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()

        videos = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId", "")
            thumbnails = snippet.get("thumbnails", {})
            thumbnail_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url", "")
            )
            videos.append(
                YoutubeVideo(
                    title=snippet.get("title", ""),
                    thumbnail_url=thumbnail_url,
                    channel_name=snippet.get("channelTitle", ""),
                    published_at=snippet.get("publishedAt", ""),
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                )
            )

        page_info = data.get("pageInfo", {})
        total_results = page_info.get("totalResults", 0)
        next_page_token = data.get("nextPageToken")
        prev_page_token = data.get("prevPageToken")

        return videos, next_page_token, prev_page_token, total_results
