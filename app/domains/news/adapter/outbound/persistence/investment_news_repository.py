"""
투자 뉴스 수집 데이터 영속화 레포지토리 (PostgreSQL).

저장 순서:
  1. investment_news       — 기사 메타데이터 (title, source, link, published_at)
  2. investment_news_contents — 본문 JSONB (news_id FK로 연결)

예외 발생 시 traceback을 콘솔에 출력하고 워크플로우는 계속 진행한다.
"""

import traceback

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.investment.infrastructure.orm.investment_news_content_orm import InvestmentNewsContentOrm
from app.domains.news.infrastructure.orm.investment_news_orm import InvestmentNewsOrm


class InvestmentNewsRepository:
    """
    투자 뉴스 수집 결과를 PostgreSQL 두 테이블에 저장하는 레포지토리.

    investment_news → investment_news_contents 순으로 저장하여
    news_id FK를 cross-table 키로 동기화한다.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_articles(
        self,
        *,
        user_id: str,
        company: str | None,
        keyword_used: str,
        articles: list[dict],
    ) -> None:
        """
        수집된 기사 목록을 메타데이터 + 본문 JSONB로 나눠 저장한다.

        저장 실패 시 traceback 출력 후 예외 재전파.
        """
        try:
            for article in articles:
                # 1. 메타데이터 저장 → news_id 획득
                news_orm = InvestmentNewsOrm(
                    user_id=user_id,
                    company=company,
                    keyword_used=keyword_used,
                    title=article.get("title", ""),
                    source=article.get("source", ""),
                    link=article.get("link", ""),
                    published_at=article.get("published_at"),
                )
                self._session.add(news_orm)
                await self._session.flush()  # news_id 확보
                news_id = news_orm.id

                # 2. 본문 JSONB 저장 (news_id FK 연결)
                content_orm = InvestmentNewsContentOrm(
                    news_id=news_id,
                    user_id=user_id,
                    company=company,
                    raw={
                        "title": article.get("title", ""),
                        "text": article.get("content", ""),
                        "source": article.get("source", ""),
                        "published_at": article.get("published_at", ""),
                        "link": article.get("link", ""),
                        "content_preview": article.get("content_preview", ""),
                    },
                )
                self._session.add(content_orm)

            await self._session.flush()
            print(f"[InvestmentNewsRepository] 기사 {len(articles)}건 저장 | company={company!r}")

        except Exception:
            print("[InvestmentNewsRepository] [ERROR] 뉴스 저장 실패:")
            traceback.print_exc()
            raise

    async def commit(self) -> None:
        try:
            await self._session.commit()
            print("[InvestmentNewsRepository] DB 커밋 완료")
        except Exception:
            print("[InvestmentNewsRepository] [ERROR] 커밋 실패:")
            traceback.print_exc()
            raise
