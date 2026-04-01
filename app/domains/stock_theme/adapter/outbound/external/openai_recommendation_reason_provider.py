from app.domains.stock_theme.application.port.recommendation_reason_port import RecommendationReasonPort
from app.domains.stock_theme.domain.service.recommendation_reason_service import RecommendationReasonService
from app.infrastructure.external.llm_port import LlmPort


class OpenAIRecommendationReasonProvider(RecommendationReasonPort):
    def __init__(self, llm: LlmPort):
        self._llm = llm

    async def generate_reason(
        self,
        stock_name: str,
        matched_keywords: list[str],
        themes: list[str],
    ) -> str:
        prompt = RecommendationReasonService.build_prompt(
            stock_name=stock_name,
            matched_keywords=matched_keywords,
            themes=themes,
        )
        return await self._llm.generate(prompt)
