from dataclasses import dataclass
from typing import Optional


@dataclass
class Account:
    account_id: Optional[int]
    email: str
    nickname: Optional[str]
    kakao_id: Optional[int]
