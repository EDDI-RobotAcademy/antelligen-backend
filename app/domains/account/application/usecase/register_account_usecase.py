from app.common.exception.app_exception import AppException
from app.domains.account.application.port.out.account_repository_port import AccountRepositoryPort
from app.domains.account.application.port.out.temp_token_port import TempTokenPort
from app.domains.account.application.request.register_account_request import RegisterAccountRequest
from app.domains.account.application.response.register_account_response import RegisterAccountResponse
from app.domains.account.domain.entity.account import Account


class RegisterAccountUseCase:
    def __init__(self, account_repository: AccountRepositoryPort, temp_token_port: TempTokenPort):
        self._account_repository = account_repository
        self._temp_token_port = temp_token_port

    async def execute(self, token: str, request: RegisterAccountRequest) -> RegisterAccountResponse:
        temp_token_info = await self._temp_token_port.find_by_token(token)
        if temp_token_info is None:
            raise AppException(status_code=401, message="유효하지 않은 임시 토큰입니다.")

        account = Account(
            account_id=None,
            email=request.email,
            nickname=request.nickname,
            kakao_id=None,
        )
        saved = await self._account_repository.save(account)

        await self._temp_token_port.delete_by_token(token)

        return RegisterAccountResponse(
            account_id=saved.account_id,
            email=saved.email,
            nickname=saved.nickname,
        )
