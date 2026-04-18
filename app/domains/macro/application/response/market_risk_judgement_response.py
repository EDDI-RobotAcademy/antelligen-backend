from datetime import date, datetime
from typing import List

from pydantic import BaseModel


class MacroReferenceVideoResponse(BaseModel):
    video_id: str
    title: str
    published_at: datetime
    video_url: str


class MarketRiskJudgementResponse(BaseModel):
    reference_date: date

    # 프론트 호환 필드: contextual(3) + baseline(3) 을 합쳐 총 6줄을 제공한다.
    status: str
    reasons: List[str]

    # 세분화 필드
    contextual_status: str
    contextual_reasons: List[str]
    baseline_status: str
    baseline_reasons: List[str]

    reference_videos: List[MacroReferenceVideoResponse]
    note_available: bool
    fallback_message: str = ""
