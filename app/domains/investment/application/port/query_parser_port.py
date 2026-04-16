from abc import ABC, abstractmethod

from app.domains.investment.domain.value_object.parsed_query import ParsedQuery


class QueryParserPort(ABC):
    """투자 질문 텍스트를 구조화된 ParsedQuery로 변환하는 포트."""

    @abstractmethod
    async def parse(self, query: str) -> ParsedQuery:
        """
        자연어 질문을 파싱하여 company / intent / required_data 를 반환한다.

        Raises:
            QueryParseError: LLM 응답이 기대 형식이 아니거나 파싱 불가한 경우.
        """
        ...
