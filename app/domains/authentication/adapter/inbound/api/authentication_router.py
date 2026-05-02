from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.domains.authentication.adapter.outbound.cache.session_query_cache_impl import SessionQueryCacheImpl
from app.domains.authentication.adapter.outbound.cache.temp_token_query_cache_impl import TempTokenQueryCacheImpl
from app.domains.authentication.adapter.outbound.persistence.account_info_query_impl import AccountInfoQueryImpl
from app.domains.authentication.application.usecase.get_temp_user_info_usecase import GetTempUserInfoUseCase
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/authentication", tags=["authentication"])


@router.get("/me")
async def get_me(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    # Cookie에서 추출 (user_token → temp_token 순서: 이미 가입된 사용자 우선)
    token = request.cookies.get("user_token") or request.cookies.get("temp_token")

    # Authorization 헤더에서 추출
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise AppException(status_code=401, message="토큰이 없습니다.")

    return await GetTempUserInfoUseCase(
        temp_token_query_port=TempTokenQueryCacheImpl(redis),
        session_query_port=SessionQueryCacheImpl(redis),
        account_info_query_port=AccountInfoQueryImpl(db),
    ).execute(token=token)
