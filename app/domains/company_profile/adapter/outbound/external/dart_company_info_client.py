import logging
from typing import Optional

import httpx

from app.domains.company_profile.application.port.out.dart_company_info_port import (
    DartCompanyInfoPort,
)
from app.domains.company_profile.domain.entity.company_profile import CompanyProfile
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

DART_COMPANY_URL = "https://opendart.fss.or.kr/api/company.json"


def _clean(value: object) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if not s or s == "-":
        return None
    return s


class DartCompanyInfoClient(DartCompanyInfoPort):
    async def fetch(self, corp_code: str) -> Optional[CompanyProfile]:
        settings = get_settings()
        params = {
            "crtfc_key": settings.open_dart_api_key,
            "corp_code": corp_code,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(DART_COMPANY_URL, params=params)
                response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.error("DART company.json HTTP 오류 (corp_code=%s): %s", corp_code, exc)
            return None

        status = data.get("status")
        if status == "013":
            logger.info("DART company.json 데이터 없음: corp_code=%s", corp_code)
            return None
        if status != "000":
            logger.error("DART company.json 오류: %s - %s", status, data.get("message"))
            return None

        return CompanyProfile(
            corp_code=_clean(data.get("corp_code")) or corp_code,
            corp_name=_clean(data.get("corp_name")) or "",
            corp_name_eng=_clean(data.get("corp_name_eng")),
            stock_name=_clean(data.get("stock_name")),
            stock_code=_clean(data.get("stock_code")),
            ceo_nm=_clean(data.get("ceo_nm")),
            corp_cls=_clean(data.get("corp_cls")),
            jurir_no=_clean(data.get("jurir_no")),
            bizr_no=_clean(data.get("bizr_no")),
            adres=_clean(data.get("adres")),
            hm_url=_clean(data.get("hm_url")),
            ir_url=_clean(data.get("ir_url")),
            phn_no=_clean(data.get("phn_no")),
            fax_no=_clean(data.get("fax_no")),
            induty_code=_clean(data.get("induty_code")),
            est_dt=_clean(data.get("est_dt")),
            acc_mt=_clean(data.get("acc_mt")),
        )
