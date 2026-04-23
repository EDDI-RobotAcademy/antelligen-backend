import logging

from fastapi import APIRouter, Depends, HTTPException
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.company_profile.adapter.outbound.cache.company_profile_cache import (
    RedisCompanyProfileCache,
)
from app.domains.company_profile.adapter.outbound.external.dart_company_info_client import (
    DartCompanyInfoClient,
)
from app.domains.company_profile.application.response.company_profile_response import (
    CompanyProfileResponse,
)
from app.domains.company_profile.application.usecase.get_company_profile_usecase import (
    GetCompanyProfileUseCase,
)
from app.domains.disclosure.adapter.outbound.persistence.company_repository_impl import (
    CompanyRepositoryImpl,
)
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.database.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/company-profile", tags=["company-profile"])


@router.get("/{ticker}", response_model=CompanyProfileResponse)
async def get_company_profile(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    usecase = GetCompanyProfileUseCase(
        company_repository=CompanyRepositoryImpl(db),
        dart_company_info=DartCompanyInfoClient(),
        cache=RedisCompanyProfileCache(redis),
    )
    profile = await usecase.execute(ticker)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Company profile not found for ticker '{ticker}'.",
        )
    return CompanyProfileResponse.from_entity(profile)
