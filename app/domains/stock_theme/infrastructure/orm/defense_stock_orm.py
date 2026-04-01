from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class DefenseStockOrm(Base):
    __tablename__ = "defense_stock"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    themes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
