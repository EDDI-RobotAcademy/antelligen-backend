from pydantic import BaseModel


class EditBoardRequest(BaseModel):
    title: str
    content: str
