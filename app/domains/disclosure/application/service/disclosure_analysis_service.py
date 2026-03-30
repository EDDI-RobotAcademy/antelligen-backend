import logging
import time

from app.domains.disclosure.adapter.outbound.cache.analysis_cache_adapter import AnalysisCacheAdapter
from app.domains.disclosure.adapter.outbound.external.dart_disclosure_api_client import DartDisclosureApiClient
from app.domains.disclosure.adapter.outbound.external.langchain_llm_client import LangChainLlmClient
from app.domains.disclosure.adapter.outbound.external.openai_embedding_client import OpenAIEmbeddingClient
from app.domains.disclosure.adapter.outbound.persistence.company_repository_impl import CompanyRepositoryImpl
from app.domains.disclosure.adapter.outbound.persistence.disclosure_document_repository_impl import DisclosureDocumentRepositoryImpl
from app.domains.disclosure.adapter.outbound.persistence.disclosure_repository_impl import DisclosureRepositoryImpl
from app.domains.disclosure.adapter.outbound.persistence.rag_chunk_repository_impl import RagChunkRepositoryImpl
from app.domains.disclosure.application.response.analysis_response import AnalysisResponse
from app.domains.disclosure.application.usecase.analysis_agent_graph import DisclosureAnalysisGraph
from app.infrastructure.cache.redis_client import redis_client
from app.infrastructure.database.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

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
            company = await CompanyRepositoryImpl(db).find_by_stock_code(ticker)

            if company is None:
                return AnalysisResponse(
                    status="error",
                    data={"ticker": ticker, "filings": []},
                    error_message=f"Company not found for ticker '{ticker}'.",
                )

            graph = DisclosureAnalysisGraph(
                disclosure_repo=DisclosureRepositoryImpl(db),
                doc_repo=DisclosureDocumentRepositoryImpl(db),
                rag_repo=RagChunkRepositoryImpl(db),
                embedding_port=OpenAIEmbeddingClient(),
                llm_port=LangChainLlmClient(),
                company_repo=CompanyRepositoryImpl(db),
                dart_api=DartDisclosureApiClient(),
            )

            result = await graph.invoke(ticker, company.corp_code, analysis_type)

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
