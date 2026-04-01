from pydantic import BaseModel


class RegisterAccountResponse(BaseModel):
    account_id: int
    email: str
    nickname: str
