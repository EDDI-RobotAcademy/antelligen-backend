from app.domains.account.domain.entity.account import Account
from app.domains.account.infrastructure.orm.account_orm import AccountOrm


class AccountMapper:

    @staticmethod
    def to_entity(orm: AccountOrm) -> Account:
        return Account(
            account_id=orm.id,
            email=orm.email,
            nickname=orm.nickname,
            kakao_id=orm.kakao_id,
        )
