from pydantic import BaseModel, Field


class InvestmentDecisionRequest(BaseModel):
    query: str = Field(..., description="사용자의 투자 판단 요청 질의 텍스트 (예: '한화에어로스페이스 지금 사도 될까?')")
