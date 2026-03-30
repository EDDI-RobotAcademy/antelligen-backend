import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.domains.stock.application.port.dart_financial_data_provider import (
    DartFinancialDataProvider,
)
from app.domains.stock.domain.entity.financial_ratio import FinancialRatio

logger = logging.getLogger(__name__)


class OpenDartFinancialDataProvider(DartFinancialDataProvider):
    """DART OpenAPI를 통해 재무 데이터를 가져오는 어댑터"""

    BASE_URL = "https://opendart.fss.or.kr/api"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_financial_ratios(
        self,
        corp_code: str,
        fiscal_year: str,
        report_code: str = "11011",
    ) -> Optional[FinancialRatio]:
        """
        DART API에서 재무제표를 조회하고 재무비율을 계산합니다.

        사용 엔드포인트: /fnlttSinglAcntAll.json (단일회사 전체 재무제표)
        """
        params = {
            "crtfc_key": self._api_key,
            "corp_code": corp_code,
            "bsns_year": fiscal_year,
            "reprt_code": report_code,
            "fs_div": "CFS",  # 연결재무제표 (CFS), 개별재무제표 (OFS)
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/fnlttSinglAcntAll.json",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            # DART API 응답 상태 확인
            status = data.get("status")
            if status != "000":
                # 연결재무제표가 없으면 개별재무제표로 재시도
                if status == "013":  # 조회된 데이터가 없음
                    params["fs_div"] = "OFS"
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        response = await client.get(
                            f"{self.BASE_URL}/fnlttSinglAcntAll.json",
                            params=params,
                        )
                        response.raise_for_status()
                        data = response.json()
                    if data.get("status") != "000":
                        logger.warning(
                            "[DART] 재무제표 조회 실패: corp_code=%s, status=%s, message=%s",
                            corp_code,
                            data.get("status"),
                            data.get("message"),
                        )
                        return None
                else:
                    logger.warning(
                        "[DART] API 오류: corp_code=%s, status=%s, message=%s",
                        corp_code,
                        data.get("status"),
                        data.get("message"),
                    )
                    return None

            # 재무제표 항목 추출
            items = data.get("list", [])
            if not items:
                return None

            # 재무비율 계산
            ratios = self._calculate_ratios(items, fiscal_year)

            return FinancialRatio(
                ticker="",  # UseCase에서 설정
                corp_code=corp_code,
                fiscal_year=fiscal_year,
                roe=ratios.get("roe"),
                roa=ratios.get("roa"),
                debt_ratio=ratios.get("debt_ratio"),
                per=None,  # 주가 데이터 필요 (SerpAPI에서 이미 제공)
                pbr=None,  # 주가 데이터 필요 (SerpAPI에서 이미 제공)
                collected_at=datetime.now(timezone.utc),
            )

        except httpx.HTTPStatusError as e:
            logger.error("[DART] HTTP 오류: %s", e)
            return None
        except Exception as e:
            logger.error("[DART] 예상치 못한 오류: %s", e)
            return None

    def _calculate_ratios(
        self, items: list[dict], fiscal_year: str
    ) -> dict[str, Optional[float]]:
        """재무제표 항목에서 재무비율을 계산합니다."""
        # 계정과목별 금액 추출
        accounts: dict[str, float] = {}

        for item in items:
            account_nm = item.get("account_nm", "")
            # 당기 금액 (thstrm_amount)
            amount_str = item.get("thstrm_amount", "")

            if not amount_str or amount_str == "-":
                continue

            try:
                # 쉼표 제거 후 숫자 변환
                amount = float(amount_str.replace(",", ""))
                accounts[account_nm] = amount
            except ValueError:
                continue

        # 필요한 계정과목 찾기
        # 재무상태표 항목
        total_assets = self._find_account(accounts, ["자산총계", "자산 총계"])
        total_liabilities = self._find_account(accounts, ["부채총계", "부채 총계"])
        total_equity = self._find_account(accounts, ["자본총계", "자본 총계"])

        # 손익계산서 항목
        net_income = self._find_account(
            accounts,
            ["당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익"],
        )

        ratios: dict[str, Optional[float]] = {
            "roe": None,
            "roa": None,
            "debt_ratio": None,
        }

        # ROE 계산: 당기순이익 / 자기자본 × 100
        if net_income is not None and total_equity and total_equity != 0:
            ratios["roe"] = round((net_income / total_equity) * 100, 2)

        # ROA 계산: 당기순이익 / 총자산 × 100
        if net_income is not None and total_assets and total_assets != 0:
            ratios["roa"] = round((net_income / total_assets) * 100, 2)

        # 부채비율 계산: 부채총계 / 자기자본 × 100
        if total_liabilities is not None and total_equity and total_equity != 0:
            ratios["debt_ratio"] = round((total_liabilities / total_equity) * 100, 2)

        return ratios

    def _find_account(
        self, accounts: dict[str, float], names: list[str]
    ) -> Optional[float]:
        """여러 계정과목명 중 존재하는 것을 찾습니다."""
        for name in names:
            if name in accounts:
                return accounts[name]
        return None
