from typing import List

import httpx

from app.domains.market_video.application.port.youtube_comment_search_port import YoutubeCommentSearchPort
from app.domains.market_video.domain.entity.video_comment import VideoComment

YOUTUBE_COMMENT_THREADS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"
_PAGE_BATCH_SIZE = 100  # YouTube API 최대 허용값


class YoutubeCommentSearchClient(YoutubeCommentSearchPort):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_comments(
        self,
        video_id: str,
        max_count: int,
        order: str,
    ) -> List[VideoComment]:
        comments: List[VideoComment] = []
        page_token: str | None = None

        async with httpx.AsyncClient() as client:
            while len(comments) < max_count:
                batch_size = min(_PAGE_BATCH_SIZE, max_count - len(comments))
                params: dict = {
                    "key": self._api_key,
                    "videoId": video_id,
                    "part": "snippet",
                    "order": order,
                    "maxResults": batch_size,
                    "textFormat": "plainText",
                }
                if page_token:
                    params["pageToken"] = page_token

                try:
                    response = await client.get(YOUTUBE_COMMENT_THREADS_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
                except Exception:
                    # 댓글 비활성화(403), 유효하지 않은 영상(404) 등 모두 빈 리스트로 처리
                    break

                for item in data.get("items", []):
                    top_comment = item.get("snippet", {}).get("topLevelComment", {})
                    snippet = top_comment.get("snippet", {})
                    text = snippet.get("textDisplay", "").strip()
                    if not text:
                        continue
                    comments.append(
                        VideoComment(
                            youtube_comment_id=top_comment.get("id"),
                            video_id=video_id,
                            comment_text=text,
                            author=snippet.get("authorDisplayName"),
                            like_count=int(snippet.get("likeCount", 0)),
                            published_at=snippet.get("publishedAt"),
                        )
                    )

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return comments[:max_count]
