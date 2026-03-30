import json
import logging
from datetime import datetime, timedelta
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, END

from app.domains.disclosure.application.port.disclosure_document_repository_port import DisclosureDocumentRepositoryPort
from app.domains.disclosure.application.port.disclosure_repository_port import DisclosureRepositoryPort
from app.domains.disclosure.application.port.embedding_port import EmbeddingPort
from app.domains.disclosure.application.port.llm_analysis_port import LlmAnalysisPort
from app.domains.disclosure.application.port.rag_chunk_repository_port import RagChunkRepositoryPort
from app.domains.disclosure.application.port.company_repository_port import CompanyRepositoryPort
from app.domains.disclosure.application.port.dart_disclosure_api_port import DartDisclosureApiPort
from app.domains.disclosure.domain.entity.disclosure import Disclosure
from app.domains.disclosure.domain.service.analysis_prompt_builder import AnalysisPromptBuilder
from app.domains.disclosure.domain.service.disclosure_classifier import DisclosureClassifier

logger = logging.getLogger(__name__)

RAG_SEARCH_LIMIT = 5
RAG_REFINE_LIMIT = 3
MAX_ITERATIONS = 3
CONFIDENCE_THRESHOLD = 0.6


class AnalysisAgentState(TypedDict):
    # Input
    ticker: str
    corp_code: str
    analysis_type: str

    # Gathered data
    disclosures: list
    rag_contexts: list
    filings: list
    summary_map: dict
    is_lightweight: bool

    # Loop control
    iteration: int
    confidence: float
    quality_issues: list
    refinement_queries: list

    # Output
    analysis_result: Optional[dict]
    status: str
    error_message: Optional[str]


class DisclosureAnalysisGraph:
    """LangGraph-based disclosure analysis agent.

    Replaces the fixed pipeline with a multi-step agent that can
    re-analyze up to MAX_ITERATIONS times when quality is insufficient.
    """

    def __init__(
        self,
        disclosure_repo: DisclosureRepositoryPort,
        doc_repo: DisclosureDocumentRepositoryPort,
        rag_repo: RagChunkRepositoryPort,
        embedding_port: EmbeddingPort,
        llm_port: LlmAnalysisPort,
        company_repo: CompanyRepositoryPort,
        dart_api: DartDisclosureApiPort,
    ):
        self._disclosure_repo = disclosure_repo
        self._doc_repo = doc_repo
        self._rag_repo = rag_repo
        self._embedding = embedding_port
        self._llm = llm_port
        self._company_repo = company_repo
        self._dart_api = dart_api
        self._graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AnalysisAgentState)

        builder.add_node("gather_disclosures", self._gather_disclosures)
        builder.add_node("classify_and_search_rag", self._classify_and_search_rag)
        builder.add_node("fetch_summaries", self._fetch_summaries)
        builder.add_node("analyze", self._analyze)
        builder.add_node("evaluate_quality", self._evaluate_quality)
        builder.add_node("refine_and_retry", self._refine_and_retry)

        builder.set_entry_point("gather_disclosures")
        builder.add_edge("gather_disclosures", "classify_and_search_rag")
        builder.add_edge("classify_and_search_rag", "fetch_summaries")
        builder.add_edge("fetch_summaries", "analyze")
        builder.add_edge("analyze", "evaluate_quality")
        builder.add_conditional_edges(
            "evaluate_quality",
            self._should_retry,
            {"retry": "refine_and_retry", "finish": END},
        )
        builder.add_edge("refine_and_retry", "analyze")

        return builder.compile()

    async def invoke(self, ticker: str, corp_code: str, analysis_type: str) -> dict:
        initial_state: AnalysisAgentState = {
            "ticker": ticker,
            "corp_code": corp_code,
            "analysis_type": analysis_type,
            "disclosures": [],
            "rag_contexts": [],
            "filings": [],
            "summary_map": {},
            "is_lightweight": False,
            "iteration": 0,
            "confidence": 0.0,
            "quality_issues": [],
            "refinement_queries": [],
            "analysis_result": None,
            "status": "in_progress",
            "error_message": None,
        }
        try:
            result = await self._graph.ainvoke(initial_state)
            result["status"] = "success"
            return result
        except Exception as e:
            logger.error("Agent graph failed: %s", str(e))
            return {**initial_state, "status": "error", "error_message": str(e)}

    # ------------------------------------------------------------------
    # Node: gather_disclosures
    # ------------------------------------------------------------------

    async def _gather_disclosures(self, state: AnalysisAgentState) -> dict:
        corp_code = state["corp_code"]
        ticker = state["ticker"]

        disclosures = await self._disclosure_repo.find_by_corp_code(corp_code, limit=50)

        if not disclosures:
            logger.info("[Agent] No disclosures in DB, falling back to DART API: corp_code=%s", corp_code)
            return await self._gather_lightweight(corp_code, ticker)

        await self._company_repo.mark_as_collect_target(corp_code)

        filings = self._build_filings(disclosures)

        logger.info("[Agent][gather_disclosures] Found %d disclosures for %s", len(disclosures), corp_code)
        return {"disclosures": disclosures, "filings": filings}

    async def _gather_lightweight(self, corp_code: str, ticker: str) -> dict:
        end_date = datetime.now().strftime("%Y%m%d")
        bgn_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")

        dart_items = await self._dart_api.fetch_all_pages(
            bgn_de=bgn_date, end_de=end_date, corp_code=corp_code,
        )

        await self._company_repo.mark_as_collect_target(corp_code)

        if not dart_items:
            return {"disclosures": [], "filings": {"core": [], "other_summary": {}}, "is_lightweight": True}

        temp_disclosures = [
            Disclosure(
                rcept_no=item.rcept_no,
                corp_code=item.corp_code,
                report_nm=item.report_nm,
                rcept_dt=datetime.strptime(item.rcept_dt, "%Y%m%d").date(),
                pblntf_ty=item.pblntf_ty,
                pblntf_detail_ty=item.pblntf_detail_ty,
                rm=item.rm,
                disclosure_group=DisclosureClassifier.classify_group(item.report_nm),
                source_mode="ondemand",
                is_core=DisclosureClassifier.is_core_disclosure(item.report_nm),
            )
            for item in dart_items
        ]

        filings = self._build_filings(temp_disclosures)
        return {"disclosures": temp_disclosures, "filings": filings, "is_lightweight": True}

    # ------------------------------------------------------------------
    # Node: classify_and_search_rag
    # ------------------------------------------------------------------

    async def _classify_and_search_rag(self, state: AnalysisAgentState) -> dict:
        disclosures = state["disclosures"]
        corp_code = state["corp_code"]
        analysis_type = state["analysis_type"]

        if not disclosures:
            return {"rag_contexts": []}

        event_disclosures = [
            d for d in disclosures
            if DisclosureClassifier.classify_group(d.report_nm) == "event"
        ]

        # Use event disclosures for signal analysis
        if analysis_type == "signal_analysis" and event_disclosures:
            analysis_disclosures = event_disclosures
        else:
            analysis_disclosures = disclosures

        # Build RAG query
        query = self._build_analysis_query(corp_code, disclosures, event_disclosures)

        # Embed and search
        try:
            query_embedding = await self._embedding.generate(query)
            rag_contexts = await self._rag_repo.search_similar(
                embedding=query_embedding, limit=RAG_SEARCH_LIMIT, corp_code=corp_code,
            )
            logger.info("[Agent][classify_and_search_rag] RAG search returned %d chunks", len(rag_contexts))
        except Exception as e:
            logger.warning("[Agent][classify_and_search_rag] RAG search failed, proceeding without: %s", e)
            rag_contexts = []

        return {
            "disclosures": analysis_disclosures,
            "rag_contexts": rag_contexts,
        }

    # ------------------------------------------------------------------
    # Node: fetch_summaries
    # ------------------------------------------------------------------

    async def _fetch_summaries(self, state: AnalysisAgentState) -> dict:
        disclosures = state["disclosures"]
        core_disclosures = [d for d in disclosures if getattr(d, "is_core", False)]
        core_rcept_nos = [d.rcept_no for d in core_disclosures]

        if not core_rcept_nos:
            return {"summary_map": {}}

        summary_map = await self._doc_repo.find_summaries_by_rcept_nos(core_rcept_nos)

        # Generate missing summaries via LLM
        missing = [r for r in core_rcept_nos if r not in summary_map]
        if missing:
            new_summaries = await self._generate_missing_summaries(missing)
            summary_map.update(new_summaries)

        logger.info("[Agent][fetch_summaries] Summaries: %d found, %d generated", len(summary_map) - len(missing), len(missing))
        return {"summary_map": summary_map}

    # ------------------------------------------------------------------
    # Node: analyze
    # ------------------------------------------------------------------

    async def _analyze(self, state: AnalysisAgentState) -> dict:
        disclosures = state["disclosures"]
        rag_contexts = state["rag_contexts"]
        summary_map = state["summary_map"]
        analysis_type = state["analysis_type"]
        iteration = state["iteration"]

        if not disclosures:
            return {
                "analysis_result": {
                    "signal": "neutral",
                    "confidence": 0.0,
                    "summary": "No disclosures available for analysis.",
                    "key_points": [],
                },
            }

        prompt, system_message = self._build_prompt(analysis_type, disclosures, rag_contexts, summary_map)

        try:
            raw_response = await self._llm.analyze(prompt, system_message)
            result = self._parse_llm_response(raw_response)
            logger.info("[Agent][analyze] Iteration %d complete: signal=%s, confidence=%.2f",
                        iteration, result.get("signal"), result.get("confidence", 0.0))
        except Exception as e:
            logger.error("[Agent][analyze] LLM call failed: %s", e)
            result = {
                "signal": "neutral",
                "confidence": 0.0,
                "summary": f"LLM analysis error: {str(e)}",
                "key_points": [],
            }

        return {"analysis_result": result}

    # ------------------------------------------------------------------
    # Node: evaluate_quality
    # ------------------------------------------------------------------

    async def _evaluate_quality(self, state: AnalysisAgentState) -> dict:
        result = state["analysis_result"] or {}
        confidence = result.get("confidence", 0.0)
        issues = []

        if confidence < 0.4:
            issues.append("low_confidence")
        if not result.get("key_points"):
            issues.append("missing_key_points")
        if len(result.get("summary", "")) < 50:
            issues.append("summary_too_short")
        if not state["rag_contexts"] and not state["is_lightweight"]:
            issues.append("no_rag_evidence")

        refinement_queries = []
        if issues:
            corp_code = state["corp_code"]
            refinement_queries = [
                f"{corp_code} major disclosure events recent",
                f"{state['ticker']} earnings dividend capital",
            ]

        iteration = state["iteration"] + 1
        logger.info("[Agent][evaluate_quality] Iteration %d: confidence=%.2f, issues=%s",
                    iteration, confidence, issues or "none")

        return {
            "confidence": confidence,
            "quality_issues": issues,
            "refinement_queries": refinement_queries,
            "iteration": iteration,
        }

    # ------------------------------------------------------------------
    # Node: refine_and_retry
    # ------------------------------------------------------------------

    async def _refine_and_retry(self, state: AnalysisAgentState) -> dict:
        corp_code = state["corp_code"]
        existing_contexts = state["rag_contexts"]
        existing_hashes = {getattr(c, "chunk_hash", None) for c in existing_contexts}

        new_contexts = []
        for query in state["refinement_queries"]:
            try:
                embedding = await self._embedding.generate(query)
                results = await self._rag_repo.search_similar(
                    embedding=embedding, limit=RAG_REFINE_LIMIT, corp_code=corp_code,
                )
                for chunk in results:
                    if getattr(chunk, "chunk_hash", None) not in existing_hashes:
                        new_contexts.append(chunk)
                        existing_hashes.add(getattr(chunk, "chunk_hash", None))
            except Exception as e:
                logger.warning("[Agent][refine_and_retry] Refinement RAG search failed: %s", e)

        logger.info("[Agent][refine_and_retry] Added %d new RAG chunks", len(new_contexts))

        return {
            "rag_contexts": existing_contexts + new_contexts,
            "quality_issues": [],
            "refinement_queries": [],
        }

    # ------------------------------------------------------------------
    # Conditional edge
    # ------------------------------------------------------------------

    @staticmethod
    def _should_retry(state: AnalysisAgentState) -> str:
        if state["iteration"] >= MAX_ITERATIONS:
            logger.info("[Agent] Max iterations (%d) reached, finishing", MAX_ITERATIONS)
            return "finish"
        if state["confidence"] >= CONFIDENCE_THRESHOLD:
            return "finish"
        if not state["quality_issues"]:
            return "finish"
        logger.info("[Agent] Retrying analysis (iteration %d)", state["iteration"])
        return "retry"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filings(disclosures: list) -> dict:
        """Build filings dict: core disclosures listed in detail, others summarized by category count."""
        core = []
        other_counts: dict[str, int] = {}

        for d in disclosures:
            is_core = getattr(d, "is_core", False)
            group = DisclosureClassifier.classify_group(d.report_nm)

            if is_core:
                rcept_dt = d.rcept_dt
                filed_at = rcept_dt.isoformat() if hasattr(rcept_dt, "isoformat") else str(rcept_dt)
                core.append({
                    "title": d.report_nm,
                    "filed_at": filed_at,
                    "type": group,
                })
            else:
                category = DisclosureClassifier.classify_event_type(d.report_nm)
                other_counts[category] = other_counts.get(category, 0) + 1

        return {"core": core, "other_summary": other_counts}

    async def _generate_missing_summaries(self, rcept_nos: list[str]) -> dict[str, str]:
        result = {}
        for rcept_no in rcept_nos:
            docs = await self._doc_repo.find_by_rcept_no(rcept_no)
            if not docs:
                continue
            doc = next((d for d in docs if d.raw_text and len(d.raw_text) > 100), None)
            if not doc:
                continue
            try:
                raw_excerpt = doc.raw_text[:3000]
                summary = await self._llm.analyze(
                    prompt=f"Summarize this disclosure in 3-5 sentences. Include key numbers and amounts.\n\n{raw_excerpt}",
                    system_message="You are a Korean financial disclosure summarization expert. Output only the summary.",
                )
                summary = summary.strip()[:500]
                doc.summary_text = summary
                await self._doc_repo.upsert(doc)
                result[rcept_no] = summary
            except Exception as e:
                logger.warning("[Agent] Summary generation failed: rcept_no=%s, %s", rcept_no, e)
        return result

    @staticmethod
    def _build_analysis_query(corp_code: str, disclosures: list, event_disclosures: list) -> str:
        parts = [f"corp_code {corp_code} disclosure analysis"]
        if event_disclosures:
            parts.append(" ".join(d.report_nm for d in event_disclosures[:5]))
        elif disclosures:
            parts.append(" ".join(d.report_nm for d in disclosures[:3]))
        return " ".join(parts)

    @staticmethod
    def _build_prompt(analysis_type: str, disclosures: list, rag_contexts: list, summary_map: dict = None) -> tuple:
        if analysis_type == "flow_analysis":
            return AnalysisPromptBuilder.build_flow_analysis_prompt(disclosures, rag_contexts, summary_map)
        elif analysis_type == "signal_analysis":
            return AnalysisPromptBuilder.build_signal_analysis_prompt(disclosures, rag_contexts, summary_map)
        else:
            return AnalysisPromptBuilder.build_full_analysis_prompt(disclosures, rag_contexts, summary_map)

    @staticmethod
    def _parse_llm_response(raw_response: str) -> dict:
        text = raw_response.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            parsed = json.loads(text)

            signal = parsed.get("overall_signal") or parsed.get("signal", "neutral")

            confidence = parsed.get("confidence", 0.5)
            if isinstance(confidence, str):
                try:
                    confidence = float(confidence)
                except ValueError:
                    confidence = 0.5

            summary = (
                parsed.get("investment_summary")
                or parsed.get("timeline_summary")
                or parsed.get("company_overview")
                or parsed.get("summary", "")
            )

            key_points = []
            for event in parsed.get("key_events", []):
                date = event.get("date", "")
                desc = event.get("event", "")
                key_points.append(f"[{date}] {desc}" if date else desc)
            for sig in parsed.get("signals", []):
                direction = sig.get("direction", "")
                desc = sig.get("description", "")
                key_points.append(f"[{direction}] {desc}" if direction else desc)
            if not key_points:
                key_points = parsed.get("risk_factors", []) + parsed.get("positive_signals", [])
            if not key_points:
                key_points = parsed.get("key_points", [])

            return {
                "signal": signal,
                "confidence": confidence,
                "summary": summary,
                "key_points": key_points,
            }
        except (json.JSONDecodeError, ValueError):
            logger.warning("[Agent] LLM response JSON parse failed")
            return {
                "signal": "neutral",
                "confidence": 0.5,
                "summary": raw_response[:500],
                "key_points": [],
            }
