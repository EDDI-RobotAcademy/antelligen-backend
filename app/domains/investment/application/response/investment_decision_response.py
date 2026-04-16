from pydantic import BaseModel


class InvestmentDecisionResponse(BaseModel):
    query: str
    final_response: str
    disclaimer: str
    iteration_count: int
