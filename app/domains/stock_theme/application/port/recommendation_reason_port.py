from abc import ABC, abstractmethod


class RecommendationReasonPort(ABC):
    @abstractmethod
    async def generate_reason(
        self,
        stock_name: str,
        matched_keywords: list[str],
        themes: list[str],
    ) -> str:
        """키워드와 테마를 기반으로 추천 이유 문장을 생성하여 반환한다."""
        pass
