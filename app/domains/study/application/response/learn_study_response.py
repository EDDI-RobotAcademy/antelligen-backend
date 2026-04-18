from typing import List

from pydantic import BaseModel


class ProcessedVideoSummary(BaseModel):
    video_id: str
    title: str
    program_type: str
    stock_count: int


class LearnStudyResponse(BaseModel):
    file_path: str
    processed_count: int
    skipped_duplicate_count: int
    total_candidates: int
    processed_videos: List[ProcessedVideoSummary]
    message: str = ""
