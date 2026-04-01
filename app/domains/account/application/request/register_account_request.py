from pydantic import BaseModel


class RegisterAccountRequest(BaseModel):
    nickname: str
    email: str
