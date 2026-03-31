from functools import lru_cache

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.infrastructure.config.settings import get_settings

_MODEL = "gpt-4.1-nano"

_SYSTEM_PROMPT = """당신은 대한민국 방산(방위산업) 주식 전문 분석가입니다.
아래에 제공된 최근 키워드 동향과 종목/테마 데이터를 참고하여 사용자의 질문에 답변하세요.

**답변 범위 규칙**:
- 방산, 방위산업, 국방, 군사, 무기, 전쟁, 안보, 주식, 종목, 테마, 투자, 추천 등과 조금이라도 관련된 질문은 적극적으로 답변하세요.
- 명백히 방산과 무관한 질문(예: 요리, 날씨, 스포츠, 연예 등)에만 다음과 같이 안내하세요:
  "죄송합니다. 해당 질문은 방산 분야의 범위를 벗어납니다. 방산 관련 주식, 테마, 키워드에 관한 질문에 답변해 드릴 수 있습니다."
- 질문이 짧거나 모호하더라도 방산 주식 맥락으로 해석될 수 있으면 답변하세요.
- 데이터 기반으로 구체적이고 유익한 답변을 제공하세요.

{context}"""


class LangChainLlmClient:
    def __init__(self, api_key: str):
        llm = ChatOpenAI(model=_MODEL, api_key=api_key)
        prompt = ChatPromptTemplate.from_messages([
            ("system", _SYSTEM_PROMPT),
            ("human", "{question}"),
        ])
        self._chain = prompt | llm | StrOutputParser()

    async def generate_answer(self, question: str, context: str) -> str:
        return await self._chain.ainvoke({"context": context, "question": question})


@lru_cache
def get_langchain_llm_client() -> LangChainLlmClient:
    settings = get_settings()
    return LangChainLlmClient(api_key=settings.openai_api_key)
