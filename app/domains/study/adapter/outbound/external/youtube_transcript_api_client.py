import asyncio
import logging
from typing import Optional

from app.domains.study.application.port.out.transcript_fetch_port import TranscriptFetchPort

logger = logging.getLogger(__name__)

PREFERRED_LANGUAGES = ["ko", "en"]


class YoutubeTranscriptApiClient(TranscriptFetchPort):
    async def fetch(self, video_id: str) -> Optional[str]:
        print(f"[study.transcript] video_id={video_id} 자막 요청")
        try:
            text = await asyncio.to_thread(self._fetch_sync, video_id)
            print(
                f"[study.transcript] video_id={video_id} 자막 길이={len(text) if text else 0}자"
            )
            return text
        except Exception as exc:
            print(f"[study.transcript] ❌ video_id={video_id} 자막 추출 실패: {exc}")
            logger.warning(
                "[study.transcript] video_id=%s 스크립트 추출 실패: %s", video_id, exc
            )
            return None

    @staticmethod
    def _fetch_sync(video_id: str) -> Optional[str]:
        from youtube_transcript_api import YouTubeTranscriptApi

        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id, languages=PREFERRED_LANGUAGES
            )
        except Exception:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        segments = [seg.get("text", "").strip() for seg in transcript_list]
        text = " ".join(s for s in segments if s)
        return text or None
