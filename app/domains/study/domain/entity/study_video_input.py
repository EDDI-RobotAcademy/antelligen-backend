from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StudyVideoInput:
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_name: str
    published_at: datetime
    collected_at: datetime = field(default_factory=datetime.now)
    transcript: Optional[str] = None
