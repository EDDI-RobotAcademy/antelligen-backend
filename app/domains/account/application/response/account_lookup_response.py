from typing import Optional

from pydantic import BaseModel


class AccountLookupResponse(BaseModel):
    is_registered: bool
    account_id: Optional[int] = None
    email: Optional[str] = None
    nickname: Optional[str] = None
    kakao_id: Optional[int] = None
