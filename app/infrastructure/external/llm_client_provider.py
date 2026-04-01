from app.infrastructure.config.settings import get_settings
from app.infrastructure.external.llm_port import LlmPort
from app.infrastructure.external.openai_llm_client import OpenAILlmClient


def get_llm_client() -> LlmPort:
    settings = get_settings()
    return OpenAILlmClient(api_key=settings.openai_api_key)
