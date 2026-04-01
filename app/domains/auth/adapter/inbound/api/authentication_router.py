import redis.asyncio as aioredis
from fastapi import APIRouter, Cookie, Depends

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.auth.adapter.outbound.cache.temp_token_query_adapter import TempTokenQueryAdapter
from app.domains.auth.application.usecase.get_temp_user_info_usecase import GetTempUserInfoUseCase
from app.infrastructure.cache.redis_client import get_redis

router = APIRouter(prefix="/authentication", tags=["authentication"])


@router.get("/me")
async def get_temp_user_info(
    temp_token: str | None = Cookie(default=None),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not temp_token:
        raise AppException(status_code=401, message="임시 토큰이 없습니다.")

    usecase = GetTempUserInfoUseCase(
        temp_token_port=TempTokenQueryAdapter(redis),
    )
    result = await usecase.execute(token=temp_token)
    return BaseResponse.ok(data=result)
