from sqlalchemy import String, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class AccountOrm(Base):
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    nickname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kakao_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
