from abc import ABC, abstractmethod


class InvestmentWorkflowPort(ABC):
    """LangGraph 투자 판단 워크플로우 실행 포트."""

    @abstractmethod
    async def run(self, *, user_id: str, query: str) -> dict:
        """워크플로우를 실행하고 최종 상태를 반환한다."""
        ...
