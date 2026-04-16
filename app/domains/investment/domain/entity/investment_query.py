from dataclasses import dataclass


@dataclass
class InvestmentQuery:
    """사용자의 투자 판단 질의를 표현하는 도메인 엔티티."""

    user_id: str
    query_text: str
