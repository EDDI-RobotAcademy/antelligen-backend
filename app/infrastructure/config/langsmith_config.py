import os

from app.infrastructure.config.settings import get_settings


def configure_langsmith() -> None:
    """Set LangSmith environment variables for automatic tracing.

    LangChain/LangGraph auto-detect these env vars — no code-level
    instrumentation needed.
    """
    settings = get_settings()
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
