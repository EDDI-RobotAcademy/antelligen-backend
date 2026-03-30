from datetime import datetime
from typing import Optional

from app.domains.stock.application.port.corp_code_repository import CorpCodeRepository
from app.domains.stock.application.port.dart_financial_data_provider import (
    DartFinancialDataProvider,
)
from app.domains.stock.application.response.dart_financial_ratio_response import (
    DartFinancialRatioResponse,
)


class FetchDartFinancialRatiosUseCase:
    """DART API에서 재무비율을 조회하는 UseCase"""

    def __init__(
        self,
        corp_code_repository: CorpCodeRepository,
        dart_financial_data_provider: DartFinancialDataProvider,
    ):
        self._corp_code_repository = corp_code_repository
        self._dart_provider = dart_financial_data_provider

    async def execute(
        self,
        ticker: str,
        fiscal_year: Optional[str] = None,
    ) -> Optional[DartFinancialRatioResponse]:
        """
        종목코드로 재무비율을 조회합니다.

        Args:
            ticker: 종목코드 (예: "005930")
            fiscal_year: 사업연도 (예: "2024"), None이면 전년도 사용

        Returns:
            DartFinancialRatioResponse 또는 None
        """
        # 1. 종목코드로 DART 고유번호 조회
        mapping = await self._corp_code_repository.find_by_ticker(ticker)
        if mapping is None:
            return None

        # 2. 사업연도 결정 (기본: 전년도)
        if fiscal_year is None:
            fiscal_year = str(datetime.now().year - 1)

        # 3. DART API에서 재무비율 조회
        ratios = await self._dart_provider.fetch_financial_ratios(
            corp_code=mapping.corp_code,
            fiscal_year=fiscal_year,
        )

        if ratios is None:
            return None

        # 4. 응답 DTO 생성
        return DartFinancialRatioResponse(
            ticker=ticker,
            corp_code=mapping.corp_code,
            corp_name=mapping.corp_name,
            fiscal_year=fiscal_year,
            roe=ratios.roe,
            roa=ratios.roa,
            per=ratios.per,
            pbr=ratios.pbr,
            debt_ratio=ratios.debt_ratio,
            collected_at=ratios.collected_at,
        )
