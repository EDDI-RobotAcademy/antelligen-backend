from typing import List, Optional

from pydantic import BaseModel


class CollectedCommentItem(BaseModel):
    youtube_comment_id: Optional[str]
    video_id: str
    author: Optional[str]
    comment_text: str
    like_count: int
    published_at: Optional[str]


class CollectCommentsResponse(BaseModel):
    total_collected: int
    new_saved: int
    skipped_duplicates: int
    comments: List[CollectedCommentItem]
