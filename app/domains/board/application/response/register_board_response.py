from datetime import datetime

from pydantic import BaseModel


class RegisterBoardResponse(BaseModel):
    board_id: int
    title: str
    content: str
    account_id: int
    created_at: datetime
    updated_at: datetime
