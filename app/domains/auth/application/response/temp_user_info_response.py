from typing import Optional

from pydantic import BaseModel


class TempUserInfoResponse(BaseModel):
    is_registered: bool = False
    nickname: Optional[str] = None
    email: Optional[str] = None
