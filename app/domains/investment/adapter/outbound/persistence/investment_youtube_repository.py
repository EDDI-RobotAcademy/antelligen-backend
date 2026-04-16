"""
YouTube/뉴스 수집 데이터 영속화 레포지토리 (PostgreSQL).

저장 테이블:
  - investment_youtube_logs       — 워크플로우 실행 로그
  - investment_youtube_videos     — 수집된 YouTube 영상
  - investment_youtube_video_comments — 영상 댓글
  - investment_news_contents      — SERP 뉴스 원문 (JSONB)

예외 발생 시 traceback을 콘솔에 출력하여 즉시 진단 가능하게 한다.
"""

import traceback

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.investment.infrastructure.orm.investment_news_content_orm import InvestmentNewsContentOrm
from app.domains.investment.infrastructure.orm.investment_youtube_log_orm import InvestmentYoutubeLogOrm
from app.domains.investment.infrastructure.orm.investment_youtube_video_comment_orm import InvestmentYoutubeVideoCommentOrm
from app.domains.investment.infrastructure.orm.investment_youtube_video_orm import InvestmentYoutubeVideoOrm
from app.domains.market_video.application.port.out.comment_fetch_port import CommentItem


class InvestmentYoutubeRepository:
    """
    투자 워크플로우 수집 결과를 PostgreSQL에 저장하는 레포지토리.

    단일 세션으로 YouTube 로그/영상/댓글과 뉴스 콘텐츠를 모두 관리한다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── YouTube 저장 ────────────────────────────────────────────────────────

    async def save_log(
        self,
        *,
        user_id: str,
        company: str | None,
        intent: str,
        required_data: list[str],
        source_statuses: dict,
    ) -> int:
        """워크플로우 실행 로그를 저장하고 log_id를 반환한다."""
        try:
            log = InvestmentYoutubeLogOrm(
                user_id=user_id,
                company=company,
                intent=intent,
                required_data=required_data,
                source_statuses=source_statuses,
            )
            self._session.add(log)
            await self._session.flush()
            print(f"[YoutubeRepository] 로그 저장 | log_id={log.id} | company={company!r}")
            return log.id
        except Exception:
            print("[YoutubeRepository] [ERROR] 로그 저장 실패:")
            traceback.print_exc()
            raise

    async def save_videos(self, log_id: int, videos: list[dict]) -> list[tuple[int, str]]:
        """
        YouTube 영상 목록을 저장하고 (db_video_id, video_url) 리스트를 반환한다.
        댓글 저장 시 db_video_id가 FK로 필요하다.
        """
        saved: list[tuple[int, str]] = []
        try:
            for video in videos:
                orm = InvestmentYoutubeVideoOrm(
                    log_id=log_id,
                    title=video["title"],
                    channel_name=video["channel_name"],
                    published_at=video.get("published_at_dt"),
                    video_url=video["video_url"],
                    thumbnail_url=video.get("thumbnail_url"),
                )
                self._session.add(orm)
                await self._session.flush()
                saved.append((orm.id, video["video_url"]))
            print(f"[YoutubeRepository] 영상 {len(saved)}건 저장 | log_id={log_id}")
            return saved
        except Exception:
            print("[YoutubeRepository] [ERROR] 영상 저장 실패:")
            traceback.print_exc()
            raise

    async def save_comments(self, video_db_id: int, comments: list[CommentItem]) -> None:
        """
        특정 영상의 댓글을 JSONB 배열로 저장한다 (영상 1개 = 1행).

        저장 구조:
          comments: [{"text": ..., "author": ..., "like_count": N, "published_at": ...}, ...]

        조회:
          SELECT comment->>'text' FROM investment_youtube_video_comments,
                 jsonb_array_elements(comments) AS comment;
        """
        try:
            comments_json = [
                {
                    "text": c.content,
                    "author": c.author_name,
                    "like_count": c.like_count,
                    "published_at": c.published_at.isoformat() if c.published_at else None,
                }
                for c in comments
            ]
            orm = InvestmentYoutubeVideoCommentOrm(
                video_id=video_db_id,
                comments=comments_json,
            )
            self._session.add(orm)
            print(f"[YoutubeRepository] 댓글 {len(comments)}건 → JSONB 1행 저장 | video_db_id={video_db_id}")
        except Exception:
            print("[YoutubeRepository] [ERROR] 댓글 저장 실패:")
            traceback.print_exc()
            raise

    # ── 뉴스 저장 ────────────────────────────────────────────────────────────

    async def save_news_contents(
        self,
        *,
        user_id: str,
        company: str | None,
        articles: list[dict],
    ) -> None:
        """
        SERP 뉴스 기사를 JSONB 형태로 investment_news_contents 테이블에 저장한다.

        raw 구조:
          {"title": ..., "text": ..., "source": ..., "published_at": ..., "link": ...}
        """
        try:
            for article in articles:
                orm = InvestmentNewsContentOrm(
                    user_id=user_id,
                    company=company,
                    raw={
                        "title": article.get("title", ""),
                        "text": article.get("snippet", ""),
                        "source": article.get("source", ""),
                        "published_at": article.get("published_at", ""),
                        "link": article.get("link", ""),
                    },
                )
                self._session.add(orm)
            print(f"[YoutubeRepository] 뉴스 {len(articles)}건 저장 | company={company!r}")
        except Exception:
            print("[YoutubeRepository] [ERROR] 뉴스 저장 실패:")
            traceback.print_exc()
            raise

    # ── 커밋 ─────────────────────────────────────────────────────────────────

    async def commit(self) -> None:
        """모든 변경사항을 트랜잭션으로 커밋한다."""
        try:
            await self._session.commit()
            print("[YoutubeRepository] DB 커밋 완료")
        except Exception:
            print("[YoutubeRepository] [ERROR] DB 커밋 실패:")
            traceback.print_exc()
            raise
