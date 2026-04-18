import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.domains.study.application.port.out.video_source_port import VideoSourcePort
from app.domains.study.domain.entity.study_video_input import StudyVideoInput

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class YoutubeVideoSourceClient(VideoSourcePort):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_by_channels(
        self,
        channel_ids: List[str],
        published_after: Optional[datetime] = None,
        max_per_channel: int = 20,
    ) -> List[StudyVideoInput]:
        if not channel_ids:
            print("[study.source] channel_ids 비어있음 — 빈 리스트 반환")
            return []
        if not self._api_key:
            print("[study.source] ⚠ youtube_api_key 미설정 — 영상 수집 생략")
            logger.warning("[study.source] youtube_api_key 미설정 — 영상 수집 생략")
            return []
        print(f"[study.source] YouTube API 조회 시작 channels={channel_ids}")

        published_after_str = (
            published_after.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if published_after
            else None
        )

        results: List[StudyVideoInput] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for channel_id in channel_ids:
                print(f"[study.source]  · channel={channel_id} search 요청")
                try:
                    search_params = {
                        "key": self._api_key,
                        "channelId": channel_id,
                        "part": "snippet",
                        "type": "video",
                        "maxResults": max_per_channel,
                        "order": "date",
                    }
                    if published_after_str:
                        search_params["publishedAfter"] = published_after_str

                    search_response = await client.get(SEARCH_URL, params=search_params)
                    if search_response.status_code != 200:
                        logger.warning(
                            "[study.source] search 실패 channel=%s status=%s",
                            channel_id,
                            search_response.status_code,
                        )
                        continue
                    search_data = search_response.json()
                    video_ids: List[str] = []
                    snippet_by_id: dict = {}
                    for item in search_data.get("items", []):
                        video_id = item.get("id", {}).get("videoId")
                        if not video_id:
                            continue
                        video_ids.append(video_id)
                        snippet_by_id[video_id] = item.get("snippet", {})

                    print(f"[study.source]    · channel={channel_id} search 결과 {len(video_ids)}건")
                    if not video_ids:
                        continue

                    details_response = await client.get(
                        VIDEOS_URL,
                        params={
                            "key": self._api_key,
                            "id": ",".join(video_ids),
                            "part": "snippet",
                        },
                    )
                    details_by_id = {}
                    if details_response.status_code == 200:
                        for item in details_response.json().get("items", []):
                            details_by_id[item.get("id")] = item.get("snippet", {})

                    collected_at = datetime.now()
                    for video_id in video_ids:
                        snippet = details_by_id.get(video_id) or snippet_by_id.get(video_id, {})
                        published_at_str = snippet.get("publishedAt", "")
                        try:
                            published_at = datetime.strptime(
                                published_at_str, "%Y-%m-%dT%H:%M:%SZ"
                            )
                        except (ValueError, TypeError):
                            published_at = datetime.utcnow()
                        results.append(
                            StudyVideoInput(
                                video_id=video_id,
                                title=snippet.get("title", ""),
                                description=snippet.get("description", ""),
                                channel_id=snippet.get("channelId", channel_id),
                                channel_name=snippet.get("channelTitle", ""),
                                published_at=published_at,
                                collected_at=collected_at,
                            )
                        )
                except Exception as exc:
                    print(f"[study.source]  ❌ channel={channel_id} 수집 실패: {exc}")
                    logger.warning(
                        "[study.source] channel=%s 수집 실패: %s",
                        channel_id,
                        exc,
                    )
                    continue

        print(f"[study.source] ▣ 최종 수집 영상 수 = {len(results)}")
        return results
