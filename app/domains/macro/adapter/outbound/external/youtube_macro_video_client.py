import logging
from datetime import datetime
from typing import List

import httpx

from app.domains.macro.application.port.out.macro_video_fetch_port import MacroVideoFetchPort
from app.domains.macro.domain.entity.macro_reference_video import MacroReferenceVideo

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
MAX_RESULTS_PER_PAGE = 50


class YoutubeMacroVideoClient(MacroVideoFetchPort):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_recent(
        self,
        channel_id: str,
        published_after: datetime,
    ) -> List[MacroReferenceVideo]:
        if not self._api_key:
            print("[macro.youtube] ⚠ youtube_api_key 미설정 — 영상 수집 생략")
            logger.warning("[macro] youtube_api_key 미설정 — 영상 수집을 건너뜁니다.")
            return []

        published_after_str = published_after.astimezone().strftime("%Y-%m-%dT%H:%M:%SZ")
        print(
            f"[macro.youtube] search 요청 channel={channel_id} "
            f"publishedAfter={published_after_str}"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            search_params = {
                "key": self._api_key,
                "channelId": channel_id,
                "part": "snippet",
                "type": "video",
                "maxResults": MAX_RESULTS_PER_PAGE,
                "publishedAfter": published_after_str,
                "order": "date",
            }
            search_response = await client.get(SEARCH_URL, params=search_params)
            if search_response.status_code != 200:
                print(
                    f"[macro.youtube] ❌ search 실패 status={search_response.status_code} "
                    f"body={search_response.text[:200]}"
                )
                logger.warning(
                    "[macro] youtube search 실패 channel=%s status=%s body=%s",
                    channel_id,
                    search_response.status_code,
                    search_response.text[:200],
                )
                return []

            search_data = search_response.json()
            video_ids: List[str] = []
            snippet_by_id: dict = {}
            for item in search_data.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if not video_id:
                    continue
                video_ids.append(video_id)
                snippet_by_id[video_id] = item.get("snippet", {})

            print(f"[macro.youtube] search 결과 {len(video_ids)}건")
            if not video_ids:
                return []

            details_params = {
                "key": self._api_key,
                "id": ",".join(video_ids),
                "part": "snippet",
            }
            details_response = await client.get(VIDEOS_URL, params=details_params)
            if details_response.status_code != 200:
                print(
                    f"[macro.youtube] ⚠ videos 상세 실패 status={details_response.status_code}"
                )
                logger.warning(
                    "[macro] youtube videos 실패 status=%s body=%s",
                    details_response.status_code,
                    details_response.text[:200],
                )
                details_items = {}
            else:
                details_items = {
                    item.get("id"): item.get("snippet", {})
                    for item in details_response.json().get("items", [])
                }
                print(f"[macro.youtube] videos 상세 수신 {len(details_items)}건")

        result: List[MacroReferenceVideo] = []
        for video_id in video_ids:
            snippet = details_items.get(video_id) or snippet_by_id.get(video_id, {})
            published_at_str = snippet.get("publishedAt", "")
            try:
                published_at = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ")
            except (ValueError, TypeError):
                published_at = datetime.utcnow()

            result.append(
                MacroReferenceVideo(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    published_at=published_at,
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                )
            )

        print(f"[macro.youtube] ▣ 최종 영상 수 = {len(result)}")
        return result
