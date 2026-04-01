from abc import ABC, abstractmethod


class LlmPort(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """프롬프트를 입력받아 생성된 텍스트를 반환한다."""
        pass
