from pydantic import BaseModel


class AnalyzeQuestionRequest(BaseModel):
    question: str
