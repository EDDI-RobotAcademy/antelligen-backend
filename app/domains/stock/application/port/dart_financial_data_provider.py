from abc import ABC, abstractmethod
from typing import Optional

from app.domains.stock.domain.entity.financial_ratio import FinancialRatio


class DartFinancialDataProvider(ABC):
    """DART API에서 재무 데이터를 가져오는 포트"""

    @abstractmethod
    async def fetch_financial_ratios(
        self,
        corp_code: str,
        fiscal_year: str,
        report_code: str = "11011",  # 11011: 사업보고서
    ) -> Optional[FinancialRatio]:
        """
        DART API에서 재무비율 데이터를 조회합니다.

        Args:
            corp_code: DART 고유번호 (8자리)
            fiscal_year: 사업연도 (예: "2024")
            report_code: 보고서 코드
                - 11013: 1분기보고서
                - 11012: 반기보고서
                - 11014: 3분기보고서
                - 11011: 사업보고서 (연간)

        Returns:
            FinancialRatio 또는 None
        """
        pass
