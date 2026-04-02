import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.domains.disclosure.application.port.llm_analysis_port import LlmAnalysisPort
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

ANALYSIS_MODEL = "gpt-5-mini"
MAX_TOKENS = 4096


class LangChainLlmClient(LlmAnalysisPort):
    """LangChain ChatOpenAI adapter implementing LlmAnalysisPort.

    Automatically traced by LangSmith when LANGCHAIN_TRACING_V2 is enabled.
    """

    def __init__(self):
        settings = get_settings()
        self._llm = ChatOpenAI(
            model=ANALYSIS_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.3,
            api_key=settings.openai_api_key,
        )

    async def analyze(self, prompt: str, system_message: str) -> str:
        try:
            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=prompt),
            ]
            response = await self._llm.ainvoke(messages)
            content = response.content
            logger.info("LLM analysis complete: model=%s, tokens=%s",
                        ANALYSIS_MODEL, response.usage_metadata.get("total_tokens", "N/A") if response.usage_metadata else "N/A")
            return content or ""
        except Exception as e:
            logger.error("LangChain LLM call failed: %s", str(e))
            raise
