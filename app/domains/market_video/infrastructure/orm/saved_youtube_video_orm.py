from datetime import datetime

from sqlalchemy import String, BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class SavedYoutubeVideoOrm(Base):
    __tablename__ = "saved_youtube_video"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    channel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[str] = mapped_column(String(50), nullable=False)
    view_count: Mapped[int] = mapped_column(BigInteger, default=0)
    thumbnail_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    video_url: Mapped[str] = mapped_column(String(500), nullable=False)
    saved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
