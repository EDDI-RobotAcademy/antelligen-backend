import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.agent.application.port.sentiment_agent_port import SentimentAgentPort
from app.domains.agent.application.response.investment_signal_response import InvestmentSignal
from app.domains.agent.application.response.sub_agent_response import AgentStatus, SubAgentResponse
from app.domains.agent.domain.value_object.source_tier import SourceTier
from app.domains.news.adapter.outbound.ticker_keyword_resolver import TickerKeywordResolver
from app.domains.sentiment.adapter.outbound.external.naver_finance_discussion_client import (
    NaverFinanceDiscussionClient,
)
from app.domains.sentiment.adapter.outbound.external.openai_sns_signal_adapter import (
    OpenAISnsSignalAdapter,
)
from app.domains.sentiment.adapter.outbound.external.reddit_client import RedditClient
from app.domains.sentiment.adapter.outbound.external.toss_community_client import TossCommunityClient
from app.domains.sentiment.adapter.outbound.persistence.sns_post_repository_impl import (
    SnsPostRepositoryImpl,
)
from app.domains.sentiment.application.usecase.analyze_sns_signal_usecase import AnalyzeSnsSignalUseCase
from app.domains.sentiment.application.usecase.collect_sns_posts_usecase import CollectSnsPostsUseCase
from app.domains.stock.adapter.outbound.persistence.stock_repository_impl import StockRepositoryImpl

logger = logging.getLogger(__name__)


class SentimentSubAgentAdapter(SentimentAgentPort):
    """
    SNS 감정분석 서브에이전트 어댑터.
    SentimentAgentPort 구현체 — sentiment_router.py와 동일한 의존성 조립 패턴.
    """

    def __init__(self, db: AsyncSession, api_key: str):
        self._db = db
        self._api_key = api_key

    async def analyze(self, ticker: str, query: str) -> SubAgentResponse:
        start_ms = int(time.time() * 1000)
        try:
            # 의존성 조립 (sentiment_router.py analyze 엔드포인트와 동일 패턴)
            repository = SnsPostRepositoryImpl(self._db)

            reddit = RedditClient()
            collectors = []
            if reddit.is_available():
                collectors.append(reddit)
            collectors.append(NaverFinanceDiscussionClient())   # API 키 불필요, 항상 추가
            collectors.append(TossCommunityClient())            # is_available=False → gather에서 skip됨
            collect_usecase = CollectSnsPostsUseCase(collectors=collectors, repository=repository)

            analysis_port = OpenAISnsSignalAdapter(api_key=self._api_key)
            keyword_resolver = TickerKeywordResolver(StockRepositoryImpl())

            usecase = AnalyzeSnsSignalUseCase(
                repository=repository,
                analysis_port=analysis_port,
                keyword_resolver=keyword_resolver,
                collect_usecase=collect_usecase,  # 게시물 부족 시 자동 수집 트리거
            )

            result = await usecase.execute(ticker)

        except Exception as e:
            elapsed = int(time.time() * 1000) - start_ms
            logger.error("[SentimentSubAgent] 분석 오류 ticker=%s: %s", ticker, e)
            return SubAgentResponse.error("sentiment", str(e), elapsed)

        elapsed = int(time.time() * 1000) - start_ms

        # 게시물 없음 → no_data 반환
        if result.total_sample_size == 0:
            return SubAgentResponse.no_data("sentiment", elapsed)

        # SnsSignalResult → SubAgentResponse 변환
        return SubAgentResponse(
            agent_name="sentiment",
            status=AgentStatus.SUCCESS,
            signal=InvestmentSignal(result.signal),       # "bullish"/"bearish"/"neutral" 그대로 매핑
            confidence=result.confidence,
            summary=result.reasoning,                      # GPT 한국어 요약
            execution_time_ms=elapsed,
            source_tier=SourceTier.LOW,                   # SNS = "하" 티어 (SourceTier.LOW)
            data={
                "ticker": ticker,
                "total_sample_size": result.total_sample_size,
            },
        )
