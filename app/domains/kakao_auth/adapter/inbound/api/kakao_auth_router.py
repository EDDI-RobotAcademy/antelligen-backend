import logging

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.account.adapter.outbound.persistence.account_repository_impl import AccountRepositoryImpl
from app.domains.account.application.usecase.find_account_by_email_usecase import FindAccountByEmailUseCase
from app.domains.kakao_auth.adapter.outbound.cache.temp_token_store import TempTokenStore
from app.domains.kakao_auth.adapter.outbound.external.kakao_token_client import KakaoTokenClient
from app.domains.kakao_auth.adapter.outbound.external.kakao_user_info_client import KakaoUserInfoClient
from app.domains.kakao_auth.application.response.kakao_callback_response import KakaoCallbackResponse, TokenType
from app.domains.kakao_auth.application.usecase.generate_kakao_oauth_url_usecase import (
    GenerateKakaoOAuthUrlUseCase,
)
from app.domains.kakao_auth.application.usecase.get_kakao_user_info_usecase import GetKakaoUserInfoUseCase
from app.domains.kakao_auth.application.usecase.issue_temp_token_usecase import IssueTempTokenUseCase
from app.domains.kakao_auth.application.usecase.request_kakao_access_token_usecase import (
    RequestKakaoAccessTokenUseCase,
)
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kakao-authentication", tags=["kakao-auth"])

settings = get_settings()


@router.get("/request-oauth-link")
async def request_oauth_link():
    try:
        usecase = GenerateKakaoOAuthUrlUseCase(
            client_id=settings.kakao_client_id,
            redirect_uri=settings.kakao_redirect_uri,
        )
        url = usecase.execute()
        return RedirectResponse(url=url)
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.get("/request-access-token-after-redirection")
async def request_access_token_after_redirection(
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if error:
        raise AppException(status_code=400, message=f"Kakao 인증 실패: {error}")
    if not code:
        raise AppException(status_code=400, message="인가 코드가 누락되었습니다.")

    try:
        kakao_token = await RequestKakaoAccessTokenUseCase(
            KakaoTokenClient(
                client_id=settings.kakao_client_id,
                redirect_uri=settings.kakao_redirect_uri,
            )
        ).execute(code)

        user_info = await GetKakaoUserInfoUseCase(
            KakaoUserInfoClient()
        ).execute(kakao_token.access_token)

        logger.info("[Kakao 사용자 정보] 닉네임: %s, 이메일: %s", user_info.nickname, user_info.email)

        account_lookup = await FindAccountByEmailUseCase(
            AccountRepositoryImpl(db)
        ).execute(user_info.email)

        if account_lookup.is_registered:
            logger.info("[회원 조회] 기존 회원 확인 — email: %s", user_info.email)
            response_data = KakaoCallbackResponse(
                token_type=TokenType.REGULAR,
                is_registered=True,
                nickname=account_lookup.nickname,
                email=account_lookup.email,
                account_id=account_lookup.account_id,
            )
            return BaseResponse.ok(data=response_data, message="기존 회원입니다.")

        # 미가입 회원 — 임시 토큰 발급
        temp_token = await IssueTempTokenUseCase(
            TempTokenStore(redis)
        ).execute(
            kakao_access_token=kakao_token.access_token,
            nickname=user_info.nickname,
            email=user_info.email,
        )

        logger.info("[임시 토큰 발급] 발급 완료 — token prefix: %s...", temp_token.token[:8])

        response_data = KakaoCallbackResponse(
            token_type=TokenType.TEMP,
            is_registered=False,
            nickname=user_info.nickname,
            email=user_info.email,
        )
        response = JSONResponse(
            content=BaseResponse.ok(data=response_data, message="미가입 회원입니다.").model_dump()
        )
        response.set_cookie(
            key="temp_token",
            value=temp_token.token,
            httponly=True,
            path="/",
            max_age=300,
        )
        return response

    except ValueError as e:
        raise AppException(status_code=400, message=str(e))
