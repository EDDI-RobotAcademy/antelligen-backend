from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.domains.market_analysis.application.port.out.llm_chain_port import LlmChainPort

_SYSTEM_PROMPT = """\
당신은 대한민국 방산 주식 시장 전문 AI 어시스턴트입니다.
아래에 제공된 방산 종목 및 테마 데이터를 기반으로 사용자의 질문에 답변합니다.

방산 도메인(방위산업, 방산주, 관련 종목 및 테마)과 무관한 질문에는 반드시 다음과 같이 안내하십시오:
"해당 질문은 방산 시장 분석 서비스의 범위를 벗어납니다. 방산 주식, 종목, 테마 관련 질문을 해주세요."

{context}
"""

_HUMAN_PROMPT = "{question}"


class LangChainAnalysisAdapter(LlmChainPort):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT),
            ("human", _HUMAN_PROMPT),
        ])
        llm = ChatOpenAI(api_key=api_key, model=model)
        self._chain = prompt | llm | StrOutputParser()

    async def analyze(self, question: str, context: str) -> str:
        return await self._chain.ainvoke({"question": question, "context": context})
