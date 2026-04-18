from dataclasses import dataclass
from datetime import datetime


@dataclass
class MacroReferenceVideo:
    video_id: str
    title: str
    description: str
    published_at: datetime
    video_url: str
