import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.domains.company_profile.application.port.out.company_profile_cache_port import (
    CompanyProfileCachePort,
)
from app.domains.company_profile.domain.entity.company_profile import CompanyProfile

logger = logging.getLogger(__name__)


class RedisCompanyProfileCache(CompanyProfileCachePort):
    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    @staticmethod
    def _key(stock_code: str) -> str:
        return f"company_profile:{stock_code}"

    async def get(self, stock_code: str) -> Optional[CompanyProfile]:
        try:
            raw = await self._redis.get(self._key(stock_code))
            if raw is None:
                return None
            payload = json.loads(raw)
            return CompanyProfile(**payload)
        except (aioredis.RedisError, json.JSONDecodeError, TypeError) as e:
            logger.warning("회사 프로필 캐시 조회 실패 (stock_code=%s): %s", stock_code, e)
            return None

    async def save(self, stock_code: str, profile: CompanyProfile, ttl_seconds: int) -> None:
        try:
            payload = {
                "corp_code": profile.corp_code,
                "corp_name": profile.corp_name,
                "corp_name_eng": profile.corp_name_eng,
                "stock_name": profile.stock_name,
                "stock_code": profile.stock_code,
                "ceo_nm": profile.ceo_nm,
                "corp_cls": profile.corp_cls,
                "jurir_no": profile.jurir_no,
                "bizr_no": profile.bizr_no,
                "adres": profile.adres,
                "hm_url": profile.hm_url,
                "ir_url": profile.ir_url,
                "phn_no": profile.phn_no,
                "fax_no": profile.fax_no,
                "induty_code": profile.induty_code,
                "est_dt": profile.est_dt,
                "acc_mt": profile.acc_mt,
            }
            await self._redis.setex(
                self._key(stock_code),
                ttl_seconds,
                json.dumps(payload, ensure_ascii=False),
            )
        except (aioredis.RedisError, TypeError) as e:
            logger.error("회사 프로필 캐시 저장 실패 (stock_code=%s): %s", stock_code, e)
