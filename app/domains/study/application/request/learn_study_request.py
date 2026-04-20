from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

DEFAULT_CHANNEL_IDS = ["UC2-YdiOkgqWzIdDwCYW1utw"]


class LearnStudyRequest(BaseModel):
    channel_ids: List[str] = Field(default_factory=lambda: list(DEFAULT_CHANNEL_IDS))
    published_after: Optional[datetime] = None
    max_per_channel: int = 20
