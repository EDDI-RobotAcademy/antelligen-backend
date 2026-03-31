from pydantic import BaseModel


class AnalyzeQuestionResponse(BaseModel):
    answer: str
