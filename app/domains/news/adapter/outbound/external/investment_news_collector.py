"""
투자 워크플로우용 뉴스 수집기 (news 도메인).

흐름:
  1. SERP API로 종목 관련 뉴스 목록 검색
  2. 각 기사 링크에 ArticleContentScraper로 접속하여 본문 추출
  3. 수집 실패한 기사는 제외하고 나머지만 반환 (부분 실패 허용)

반환 데이터는 Retrieval Agent 의 retrieval_data 에 직접 적재된다.
"""

import asyncio
import traceback

from app.domains.news.adapter.outbound.external.article_content_scraper import ArticleContentScraper
from app.domains.news.adapter.outbound.external.serp_news_search_provider import SerpNewsSearchProvider
from app.domains.news.domain.entity.news_article import NewsArticle

# 종목명이 없을 때 사용하는 기본 키워드
DEFAULT_KEYWORD = "방산 방위산업 한국 주식"
# 검색할 기사 수
_PAGE_SIZE = 5
# retrieval_data summary 최대 길이
_PREVIEW_MAX_LEN = 300


class InvestmentNewsCollector:
    """
    투자 워크플로우 Retrieval 단계에서 호출되는 뉴스 수집기.

    사용 예:
        collector = InvestmentNewsCollector(serp_api_key="...")
        articles = await collector.collect(company="한화오션")
    """

    def __init__(self, serp_api_key: str) -> None:
        self._serp = SerpNewsSearchProvider(api_key=serp_api_key)
        self._scraper = ArticleContentScraper()

    async def collect(self, company: str | None) -> list[dict]:
        """
        종목명 기반으로 뉴스를 검색하고 본문을 수집한다.

        Args:
            company: Query Parser가 추출한 종목명. None이면 DEFAULT_KEYWORD 사용.

        Returns:
            수집된 기사 목록. 각 항목은 다음 키를 포함한다:
              - title, source, link, published_at, snippet
              - content: 본문 전체 (수집 실패 시 빈 문자열)
              - content_preview: 본문 앞 300자 (없으면 snippet)
              - summary_text: Retrieval Agent 적재용 단일 텍스트
              - fetch_success: 본문 수집 성공 여부
        """
        keyword = f"{company} 주식 뉴스" if company else DEFAULT_KEYWORD
        print(f"[InvestmentNewsCollector] 뉴스 검색 시작 | keyword={keyword!r}")

        search_result = await self._serp.search(keyword=keyword, page=1, page_size=_PAGE_SIZE)
        articles = search_result.articles[:_PAGE_SIZE]  # google_news engine ignores num param → slice here
        print(f"[InvestmentNewsCollector] 검색 결과 {len(search_result.articles)}건 → {len(articles)}건으로 제한")

        # 본문 수집 병렬 실행 (부분 실패 허용)
        contents = await asyncio.gather(
            *[self._safe_fetch(a) for a in articles],
            return_exceptions=False,  # _safe_fetch 내부에서 예외 처리
        )

        result: list[dict] = []
        for article, content in zip(articles, contents):
            preview = content[:_PREVIEW_MAX_LEN] if content else article.snippet or ""
            summary = (
                f"[{article.source}] {article.title}\n"
                f"발행: {article.published_at}\n"
                f"{preview}"
            )
            result.append({
                "title": article.title,
                "source": article.source,
                "link": article.link,
                "published_at": article.published_at,
                "snippet": article.snippet,
                "content": content,
                "content_preview": preview,
                "summary_text": summary,
                "fetch_success": bool(content),
            })
            status = "본문 수집 성공" if content else "본문 수집 실패 (snippet 사용)"
            print(f"[InvestmentNewsCollector]   - {article.title[:40]!r} | {status}")

        print(f"[InvestmentNewsCollector] 수집 완료 | 성공={sum(1 for r in result if r['fetch_success'])}건 / 전체={len(result)}건")
        return result

    async def _safe_fetch(self, article: NewsArticle) -> str:
        """
        기사 본문을 수집한다. 실패 시 빈 문자열을 반환한다 (부분 실패 허용).
        """
        if not article.link:
            return ""
        try:
            content = await self._scraper.fetch_content(article.link)
            return content or ""
        except Exception as e:
            print(f"[InvestmentNewsCollector] 본문 수집 실패 (무시) | link={article.link} | {e}")
            traceback.print_exc()
            return ""
