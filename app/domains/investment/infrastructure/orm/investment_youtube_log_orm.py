from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class InvestmentYoutubeLogOrm(Base):
    """투자 워크플로우 1회 실행에 대한 YouTube 수집 로그."""

    __tablename__ = "investment_youtube_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intent: Mapped[str] = mapped_column(String(50), nullable=False)
    required_data: Mapped[list] = mapped_column(JSON, nullable=False)
    source_statuses: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
