"""추천 이유 프롬프트 생성 도메인 서비스.

키워드와 테마 정보를 기반으로 LLM에 전달할 프롬프트를 구성한다.
"""


class RecommendationReasonService:
    @staticmethod
    def build_prompt(
        stock_name: str,
        matched_keywords: list[str],
        themes: list[str],
    ) -> str:
        """추천 이유 생성을 위한 LLM 프롬프트를 반환한다."""
        keywords_str = ", ".join(matched_keywords)
        themes_str = ", ".join(themes)
        return (
            f"아래 정보를 바탕으로 주식 추천 이유를 한국어로 2~3문장으로 작성하세요.\n"
            f"종목명: {stock_name}\n"
            f"매칭된 키워드: {keywords_str}\n"
            f"종목 테마: {themes_str}\n\n"
            f"요구사항:\n"
            f"- 어떤 키워드가 어떤 테마와 연결되어 이 종목이 추천되었는지 명확히 설명하세요.\n"
            f"- 일반 투자자가 이해하기 쉬운 자연어로 작성하세요.\n"
            f"- 추천 이유 문장만 작성하고 다른 부연 설명은 포함하지 마세요."
        )
