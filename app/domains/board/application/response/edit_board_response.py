from datetime import datetime

from pydantic import BaseModel


class EditBoardResponse(BaseModel):
    board_id: int
    title: str
    content: str
    nickname: str
    created_at: datetime
    updated_at: datetime
