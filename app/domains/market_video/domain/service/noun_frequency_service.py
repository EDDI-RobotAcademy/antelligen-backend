from collections import Counter
from typing import List, Optional

from app.domains.market_video.domain.service.defense_synonym_table import SYNONYM_TO_CANONICAL

_DEFAULT_TOP_N = 30


class NounFrequencyService:
    """댓글에서 추출된 명사 목록을 받아 빈도수 기준으로 정렬하는 도메인 서비스."""

    @staticmethod
    def consolidate_synonyms(nouns: List[str]) -> List[str]:
        """동의어를 대표 키워드로 통합한다.

        SYNONYM_TO_CANONICAL 매핑 테이블을 기반으로 동의어를 대표 키워드로 변환한다.
        매핑 테이블에 없는 명사는 원래 형태를 유지한다.

        Args:
            nouns: 추출된 명사 목록

        Returns:
            동의어가 대표 키워드로 통합된 명사 목록
        """
        return [SYNONYM_TO_CANONICAL.get(noun, noun) for noun in nouns]

    @staticmethod
    def count_frequencies(nouns: List[str], top_n: Optional[int] = None) -> List[dict]:
        """명사 리스트를 받아 빈도수 기준 내림차순 정렬된 결과를 반환한다.

        Args:
            nouns: 추출된 명사 목록
            top_n: 반환할 상위 키워드 수. None이면 전체 반환.
        """
        counter = Counter(nouns)
        return [{"noun": noun, "count": count} for noun, count in counter.most_common(top_n)]
