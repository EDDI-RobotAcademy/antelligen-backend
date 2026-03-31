from app.domains.market_analysis.application.port.out.llm_port import LLMPort
from app.infrastructure.external.langchain_llm_client import LangChainLlmClient


class LangChainLLMAdapter(LLMPort):
    def __init__(self, client: LangChainLlmClient):
        self._client = client

    async def generate_answer(self, question: str, context: str) -> str:
        return await self._client.generate_answer(question, context)
