from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class InvestmentYoutubeVideoCommentOrm(Base):
    """YouTube 영상 1개의 댓글 목록을 JSONB 배열로 저장한다.

    comments 컬럼 구조 (배열):
      [
        {"text": "댓글 내용", "author": "작성자", "like_count": 3, "published_at": "..."},
        ...
      ]

    조회 예시:
      SELECT id, video_id, comment->>'text' AS comment_text
      FROM investment_youtube_video_comments,
           jsonb_array_elements(comments) AS comment;
    """

    __tablename__ = "investment_youtube_video_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("investment_youtube_videos.id"), nullable=False
    )
    comments: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
