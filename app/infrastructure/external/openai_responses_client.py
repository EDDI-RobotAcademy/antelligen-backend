import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from openai import OpenAI

from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class OpenAIResponsesResult:
    output_text: str
    model: str


class OpenAIResponsesClient:
    """OpenAI Responses API (gpt-5-mini) 공용 External Client.

    Infrastructure Layer 규칙에 따라 기술 세부사항(OpenAI SDK 초기화, API 호출)을
    이 모듈에서 관리한다. Application / Adapter 는 이 클라이언트를 직접 호출하지 않고
    도메인별 Outbound Adapter 를 통해 간접적으로 이용한다.
    """

    def __init__(self, api_key: str, model: str):
        self._client = OpenAI(api_key=api_key)
        self._model = model

    async def create(
        self,
        instructions: str,
        input_text: str,
        model: Optional[str] = None,
        text_format: Optional[Dict[str, Any]] = None,
    ) -> OpenAIResponsesResult:
        used_model = model or self._model
        print(
            f"[openai.responses] 요청 model={used_model} input_len={len(input_text)} "
            f"text_format={'on' if text_format else 'off'}"
        )
        logger.debug("[openai.responses] model=%s input_len=%d", used_model, len(input_text))

        kwargs: Dict[str, Any] = {
            "model": used_model,
            "instructions": instructions,
            "input": input_text,
        }
        if text_format is not None:
            kwargs["text"] = {"format": text_format}

        response = await asyncio.to_thread(
            self._client.responses.create,
            **kwargs,
        )
        output_text = getattr(response, "output_text", "") or ""
        print(f"[openai.responses] 응답 수신 model={used_model} output_len={len(output_text)}")
        return OpenAIResponsesResult(output_text=output_text, model=used_model)


_singleton: Optional[OpenAIResponsesClient] = None


def get_openai_responses_client() -> OpenAIResponsesClient:
    global _singleton
    if _singleton is None:
        settings = get_settings()
        _singleton = OpenAIResponsesClient(
            api_key=settings.openai_api_key,
            model=settings.openai_learning_model,
        )
    return _singleton
