from typing import Optional

from app.domains.account.application.port.out.account_repository_port import AccountRepositoryPort
from app.domains.account.application.response.account_lookup_response import AccountLookupResponse


class FindAccountByEmailUseCase:
    def __init__(self, account_repository: AccountRepositoryPort):
        self._repository = account_repository

    async def execute(self, email: Optional[str]) -> AccountLookupResponse:
        if not email:
            return AccountLookupResponse(is_registered=False)

        account = await self._repository.find_by_email(email)
        if account is None:
            return AccountLookupResponse(is_registered=False, email=email)

        return AccountLookupResponse(
            is_registered=True,
            account_id=account.account_id,
            email=account.email,
            nickname=account.nickname,
            kakao_id=account.kakao_id,
        )
