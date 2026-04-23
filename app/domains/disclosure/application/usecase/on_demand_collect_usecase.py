import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import redis.asyncio as aioredis

from app.domains.disclosure.application.port.company_repository_port import CompanyRepositoryPort
from app.domains.disclosure.application.port.dart_disclosure_api_port import DartDisclosureApiPort
from app.domains.disclosure.application.port.disclosure_repository_port import (
    DisclosureRepositoryPort,
)
from app.domains.disclosure.domain.entity.disclosure import Disclosure
from app.domains.disclosure.domain.service.disclosure_classifier import DisclosureClassifier

logger = logging.getLogger(__name__)

ON_DEMAND_PBLNTF_TYPES = ["A", "B", "C", "D", "E"]
ON_DEMAND_LOOKBACK_DAYS = 180
LOCK_TTL_SECONDS = 60
LOCK_WAIT_SECONDS = 2
LOCK_MAX_RETRIES = 15


class OnDemandCollectUseCase:
    """특정 종목의 공시를 요청 시점에 DART에서 직접 수집하여 DB에 저장한다.

    Redis 분산 락으로 동일 종목 동시 요청 시 중복 호출을 방지한다.
    """

    def __init__(
        self,
        dart_disclosure_api: DartDisclosureApiPort,
        disclosure_repository: DisclosureRepositoryPort,
        company_repository: CompanyRepositoryPort,
        redis: aioredis.Redis,
    ):
        self._dart_api = dart_disclosure_api
        self._disclosure_repo = disclosure_repository
        self._company_repo = company_repository
        self._redis = redis

    async def execute(self, corp_code: str, ticker: Optional[str] = None) -> int:
        existing = await self._disclosure_repo.find_by_corp_code(corp_code, limit=1)
        if existing:
            return 0

        lock_key = f"lock:disclosure:on_demand:{corp_code}"
        acquired = await self._acquire_lock(lock_key)

        if not acquired:
            await self._wait_for_other_request(corp_code)
            return 0

        try:
            saved = await self._collect(corp_code, ticker)
            try:
                await self._company_repo.mark_as_collect_target(corp_code)
            except Exception as e:
                logger.warning("collect_target 마킹 실패 (corp_code=%s): %s", corp_code, e)
            return saved
        finally:
            try:
                await self._redis.delete(lock_key)
            except aioredis.RedisError:
                pass

    async def _acquire_lock(self, lock_key: str) -> bool:
        try:
            return bool(await self._redis.set(lock_key, "1", nx=True, ex=LOCK_TTL_SECONDS))
        except aioredis.RedisError as e:
            logger.warning("Redis 락 획득 실패 (%s): %s — 락 없이 진행", lock_key, e)
            return True

    async def _wait_for_other_request(self, corp_code: str) -> None:
        for _ in range(LOCK_MAX_RETRIES):
            await asyncio.sleep(LOCK_WAIT_SECONDS)
            existing = await self._disclosure_repo.find_by_corp_code(corp_code, limit=1)
            if existing:
                return
        logger.warning("다른 on-demand 수집 대기 시간 초과 (corp_code=%s)", corp_code)

    async def _collect(self, corp_code: str, ticker: Optional[str]) -> int:
        end_date = datetime.now().strftime("%Y%m%d")
        bgn_date = (datetime.now() - timedelta(days=ON_DEMAND_LOOKBACK_DAYS)).strftime("%Y%m%d")

        logger.info(
            "[OnDemandCollect] 수집 시작: ticker=%s, corp_code=%s, 기간=%s~%s",
            ticker, corp_code, bgn_date, end_date,
        )

        fetch_tasks = [
            self._dart_api.fetch_all_pages(
                bgn_de=bgn_date,
                end_de=end_date,
                corp_code=corp_code,
                pblntf_ty=pblntf_ty,
            )
            for pblntf_ty in ON_DEMAND_PBLNTF_TYPES
        ]
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        all_items = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "[OnDemandCollect] DART 조회 실패 (유형=%s, corp_code=%s): %s",
                    ON_DEMAND_PBLNTF_TYPES[i], corp_code, result,
                )
                continue
            all_items.extend(result)

        if not all_items:
            logger.info("[OnDemandCollect] 공시 없음: corp_code=%s", corp_code)
            return 0

        disclosures = [
            Disclosure(
                rcept_no=item.rcept_no,
                corp_code=item.corp_code,
                report_nm=item.report_nm,
                rcept_dt=datetime.strptime(item.rcept_dt, "%Y%m%d").date(),
                pblntf_ty=item.pblntf_ty,
                pblntf_detail_ty=item.pblntf_detail_ty,
                rm=item.rm,
                disclosure_group=DisclosureClassifier.classify_group(item.report_nm),
                source_mode="on_demand",
                is_core=DisclosureClassifier.is_core_disclosure(item.report_nm),
            )
            for item in all_items
        ]

        saved = await self._disclosure_repo.upsert_bulk(disclosures)
        logger.info(
            "[OnDemandCollect] 저장 완료: ticker=%s, corp_code=%s, fetched=%d, saved=%d",
            ticker, corp_code, len(all_items), saved,
        )
        return saved
