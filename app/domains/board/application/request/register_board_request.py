from pydantic import BaseModel


class RegisterBoardRequest(BaseModel):
    title: str
    content: str
