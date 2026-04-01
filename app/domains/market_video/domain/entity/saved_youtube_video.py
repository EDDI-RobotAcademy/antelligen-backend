from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SavedYoutubeVideo:
    video_id: str
    title: str
    channel_name: str
    published_at: str
    view_count: int
    thumbnail_url: str
    video_url: str
    db_id: Optional[int] = field(default=None)
