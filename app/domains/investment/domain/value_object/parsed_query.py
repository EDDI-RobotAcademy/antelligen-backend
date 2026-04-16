"""투자 질문 파싱 결과를 표현하는 값 객체 (순수 Python)."""

from typing import Optional
from typing import TypedDict


class ParsedQuery(TypedDict):
    """LLM이 사용자 질문에서 추출한 구조화된 쿼리 데이터."""

    company: Optional[str]    # 종목명 또는 티커. 특정 종목이 없으면 None (예: 테마/섹터 질문)
    intent: str               # 질문 의도: 매수판단 | 매도판단 | 리스크분석 | 전망조회 | 테마분석 | 기타
    required_data: list[str]  # 후속 에이전트가 수집·분석해야 할 데이터 유형 목록


class QueryParseError(Exception):
    """Query Parser가 LLM 응답을 구조화된 데이터로 변환하지 못할 때 발생하는 예외."""
