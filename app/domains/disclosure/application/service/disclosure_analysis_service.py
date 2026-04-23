import json
import logging
import time

from openai import AsyncOpenAI

from app.domains.disclosure.adapter.outbound.cache.analysis_cache_adapter import AnalysisCacheAdapter
from app.domains.disclosure.adapter.outbound.external.dart_disclosure_api_client import DartDisclosureApiClient
from app.domains.disclosure.adapter.outbound.external.langchain_llm_client import LangChainLlmClient
from app.domains.disclosure.adapter.outbound.external.openai_embedding_client import OpenAIEmbeddingClient
from app.domains.disclosure.adapter.outbound.external.sec_edgar_api_client import SecEdgarApiClient
from app.domains.disclosure.adapter.outbound.persistence.company_repository_impl import CompanyRepositoryImpl
from app.domains.disclosure.adapter.outbound.persistence.disclosure_document_repository_impl import DisclosureDocumentRepositoryImpl
from app.domains.disclosure.adapter.outbound.persistence.disclosure_repository_impl import DisclosureRepositoryImpl
from app.domains.disclosure.adapter.outbound.persistence.rag_chunk_repository_impl import RagChunkRepositoryImpl
from app.domains.disclosure.application.response.analysis_response import AnalysisResponse
from app.domains.disclosure.application.usecase.analysis_agent_graph import DisclosureAnalysisGraph
from app.domains.disclosure.application.usecase.on_demand_collect_usecase import (
    OnDemandCollectUseCase,
)
from app.domains.stock.adapter.outbound.persistence.stock_repository_impl import StockRepositoryImpl
from app.domains.stock.domain.service.market_region_resolver import MarketRegionResolver
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.config.settings import get_settings
from app.infrastructure.database.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_US_DISCLOSURE_SYSTEM_PROMPT = """당신은 SEC 공시를 전문으로 분석하는 투자 분석가입니다.
최근 SEC 공시 목록을 분석하여 JSON 시그널 평가를 반환하세요.

**반드시 summary와 key_points는 한국어로 작성하세요.** 공시 form 코드(8-K, 10-K 등)는 그대로 사용해도 됩니다.

반드시 아래 JSON 형식으로만 응답 (마크다운 금지):
{
  "signal": "bullish" | "bearish" | "neutral",
  "confidence": <0.0-1.0 사이 float>,
  "summary": "<최근 공시 기반 2-3 문장 한국어 투자 의견>",
  "key_points": ["<구체 공시 기반 한국어 포인트>", ...]
}"""

DEFAULT_CACHE_TTL = 3600


class DisclosureAnalysisService:
    """Disclosure analysis agent service facade.

    Entry point called by the main agent with a ticker (stock code).
    Manages ticker -> corp_code conversion, DB/Redis connections,
    and delegates analysis to the LangGraph agent.
    """

    async def analyze(
        self,
        ticker: str,
        analysis_type: str = "full_analysis",
    ) -> AnalysisResponse:
        settings = get_settings()
        stock = await StockRepositoryImpl().find_by_ticker(ticker)
        market_hint = stock.market if stock else None
        region = MarketRegionResolver.resolve(ticker, market_hint)

        if region.is_us() and settings.enable_us_tickers:
            return await self._analyze_us(ticker, settings)

        start_time = time.monotonic()

        # Phase 0: Redis cache check (no DB access)
        cache = AnalysisCacheAdapter(redis_client)
        cached_result = await cache.get(ticker, analysis_type)
        if cached_result is not None:
            logger.info("Cache hit: ticker=%s, type=%s", ticker, analysis_type)
            return AnalysisResponse(
                data={"ticker": ticker, "filings": cached_result.get("filings", [])},
                execution_time_ms=0,
                signal=cached_result.get("signal"),
                confidence=cached_result.get("confidence"),
                summary=cached_result.get("summary"),
                key_points=cached_result.get("key_points", []),
            )

        # Phase 1+2: LangGraph agent (single DB session)
        async with AsyncSessionLocal() as db:
            company_repo = CompanyRepositoryImpl(db)
            disclosure_repo = DisclosureRepositoryImpl(db)
            company = await company_repo.find_by_stock_code(ticker)

            if company is None:
                return AnalysisResponse(
                    status="error",
                    data={"ticker": ticker, "filings": []},
                    error_message=f"Company not found for ticker '{ticker}'.",
                )

            # On-demand: top 10 외 종목은 공시가 DB에 없을 수 있음 → 즉시 수집
            if not company.is_top300:
                existing = await disclosure_repo.find_by_corp_code(company.corp_code, limit=1)
                if not existing:
                    try:
                        on_demand = OnDemandCollectUseCase(
                            dart_disclosure_api=DartDisclosureApiClient(),
                            disclosure_repository=disclosure_repo,
                            company_repository=company_repo,
                            redis=redis_client,
                        )
                        await on_demand.execute(company.corp_code, ticker)
                    except Exception as e:
                        logger.warning(
                            "[OnDemandCollect] 수집 실패 (ticker=%s, corp_code=%s): %s",
                            ticker, company.corp_code, e,
                        )

            graph = DisclosureAnalysisGraph(
                disclosure_repo=disclosure_repo,
                doc_repo=DisclosureDocumentRepositoryImpl(db),
                rag_repo=RagChunkRepositoryImpl(db),
                embedding_port=OpenAIEmbeddingClient(),
                llm_port=LangChainLlmClient(),
                company_repo=company_repo,
                dart_api=DartDisclosureApiClient(),
            )

            try:
                result = await graph.invoke(ticker, company.corp_code, analysis_type)
            except Exception as exc:
                await db.rollback()
                logger.error("DisclosureAnalysisGraph failed for ticker=%s: %s", ticker, exc)
                return AnalysisResponse(
                    status="error",
                    data={"ticker": ticker, "filings": []},
                    error_message=str(exc),
                )

        # Build response and cache
        elapsed = int((time.monotonic() - start_time) * 1000)
        analysis = result.get("analysis_result") or {}
        filings = result.get("filings", [])

        cache_data = {
            "filings": filings,
            "signal": analysis.get("signal"),
            "confidence": analysis.get("confidence"),
            "summary": analysis.get("summary"),
            "key_points": analysis.get("key_points", []),
        }
        await cache.save(ticker, analysis_type, cache_data, DEFAULT_CACHE_TTL)

        if result.get("status") == "error":
            return AnalysisResponse(
                status="error",
                data={"ticker": ticker, "filings": filings},
                error_message=result.get("error_message"),
                execution_time_ms=elapsed,
            )

        iterations = result.get("iteration", 1)
        logger.info("Analysis complete: ticker=%s, iterations=%d, confidence=%.2f, elapsed=%dms",
                    ticker, iterations, analysis.get("confidence", 0.0), elapsed)

        return AnalysisResponse(
            data={"ticker": ticker, "filings": filings},
            execution_time_ms=elapsed,
            signal=analysis.get("signal"),
            confidence=analysis.get("confidence"),
            summary=analysis.get("summary"),
            key_points=analysis.get("key_points", []),
        )

    @staticmethod
    async def _analyze_us(ticker: str, settings) -> AnalysisResponse:
        """US 종목: SEC EDGAR 공시 목록 → OpenAI 분석"""
        start_time = time.monotonic()
        sec_client = SecEdgarApiClient(user_agent=settings.sec_edgar_user_agent)
        filings = await sec_client.fetch_recent_filings(ticker, limit=20)

        if not filings:
            return AnalysisResponse(
                status="error",
                data={"ticker": ticker, "filings": []},
                error_message=f"No SEC filings found for '{ticker}'.",
            )

        filing_text = "\n".join(
            f"- [{f.form_type}] {f.filed_date}: {f.description}"
            for f in filings
        )
        prompt = f"[{ticker} Recent SEC Filings]\n{filing_text}"

        try:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model=settings.openai_finance_agent_model,
                messages=[
                    {"role": "system", "content": _US_DISCLOSURE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            data = json.loads(resp.choices[0].message.content.strip())
        except Exception as exc:
            logger.error("[SEC EDGAR] LLM analysis failed for %s: %s", ticker, exc)
            return AnalysisResponse(
                status="error",
                data={"ticker": ticker, "filings": []},
                error_message=str(exc),
            )

        elapsed = int((time.monotonic() - start_time) * 1000)
        filing_dicts = [
            {"form_type": f.form_type, "filed_date": f.filed_date, "description": f.description}
            for f in filings
        ]
        return AnalysisResponse(
            data={"ticker": ticker, "filings": filing_dicts},
            execution_time_ms=elapsed,
            signal=data.get("signal"),
            confidence=data.get("confidence"),
            summary=data.get("summary"),
            key_points=data.get("key_points", []),
        )
