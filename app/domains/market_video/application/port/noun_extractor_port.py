from abc import ABC, abstractmethod
from typing import List


class NounExtractorPort(ABC):
    @abstractmethod
    def extract_nouns(self, text: str) -> List[str]:
        pass
