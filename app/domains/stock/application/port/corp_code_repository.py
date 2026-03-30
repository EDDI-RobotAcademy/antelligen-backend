from abc import ABC, abstractmethod
from typing import Optional

from app.domains.stock.domain.entity.corp_code_mapping import CorpCodeMapping


class CorpCodeRepository(ABC):
    """종목코드-DART 고유번호 매핑 조회 포트"""

    @abstractmethod
    async def find_by_ticker(self, ticker: str) -> Optional[CorpCodeMapping]:
        """
        종목코드로 DART 고유번호 매핑을 조회합니다.

        Args:
            ticker: 종목코드 (예: "005930")

        Returns:
            CorpCodeMapping 또는 None
        """
        pass
