from app.common.exception.app_exception import AppException
from app.domains.auth.application.port.out.temp_token_query_port import TempTokenQueryPort
from app.domains.auth.application.response.temp_user_info_response import TempUserInfoResponse


class GetTempUserInfoUseCase:
    def __init__(self, temp_token_port: TempTokenQueryPort):
        self._port = temp_token_port

    async def execute(self, token: str) -> TempUserInfoResponse:
        print(f"[GetTempUserInfoUseCase] temp_token: {token}")

        user_info = await self._port.find_by_token(token)
        if user_info is None:
            raise AppException(status_code=401, message="유효하지 않은 임시 토큰이거나 만료되었습니다.")

        print(f"[GetTempUserInfoUseCase] nickname: {user_info.nickname}, email: {user_info.email}")

        return TempUserInfoResponse(
            is_registered=False,
            nickname=user_info.nickname,
            email=user_info.email,
        )
