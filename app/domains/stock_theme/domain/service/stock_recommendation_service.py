"""종목 추천 도메인 서비스.

추출된 키워드와 DB 종목 테마를 매칭하여 종목별 관련성 점수를 산출한다.
"""

from dataclasses import dataclass

from app.domains.stock_theme.domain.entity.defense_stock import DefenseStock


@dataclass
class StockRecommendation:
    stock: DefenseStock
    matched_keywords: list[str]
    relevance_score: int


class StockRecommendationService:
    """키워드-테마 매칭 및 관련성 점수 산출 도메인 서비스."""

    @staticmethod
    def recommend(
        stocks: list[DefenseStock],
        keyword_frequencies: dict[str, int],
    ) -> list[StockRecommendation]:
        """종목별 관련성 점수를 산출하고 내림차순 정렬하여 반환한다.

        관련성 점수 = 해당 종목 테마 키워드 중 추출된 키워드와 일치하는 항목의 빈도수 합산.

        Args:
            stocks: DB에 등록된 방산주 목록
            keyword_frequencies: {키워드: 빈도수} 딕셔너리

        Returns:
            관련성 점수 기준 내림차순 정렬된 추천 결과 (점수 0인 종목은 제외)
        """
        results: list[StockRecommendation] = []

        for stock in stocks:
            matched = [theme for theme in stock.themes if theme in keyword_frequencies]
            if not matched:
                continue

            score = sum(keyword_frequencies[theme] for theme in matched)
            results.append(
                StockRecommendation(
                    stock=stock,
                    matched_keywords=matched,
                    relevance_score=score,
                )
            )

        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results
