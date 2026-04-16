from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class InvestmentNewsContentOrm(Base):
    """투자 워크플로우에서 수집한 뉴스 본문 데이터 (JSONB).

    news_id 는 investment_news.id 를 참조하는 cross-table 키다.

    raw 컬럼 구조:
      {
        "title": "기사 제목",
        "text":  "본문 전체 (trafilatura 추출)",
        "source": "출처 언론사",
        "published_at": "발행일",
        "link": "원문 URL",
        "content_preview": "본문 앞 300자"
      }

    조회 예시:
      SELECT raw->>'text' FROM investment_news_contents;
    """

    __tablename__ = "investment_news_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("investment_news.id"), nullable=True, index=True
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
