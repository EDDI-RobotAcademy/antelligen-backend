from typing import List

from kiwipiepy import Kiwi

from app.domains.market_video.application.port.noun_extractor_port import NounExtractorPort

_NOUN_TAGS = {"NNG", "NNP", "NNB"}


class KiwiNounExtractor(NounExtractorPort):
    """kiwipiepy를 사용하는 한국어 명사 추출기."""

    def __init__(self):
        self._kiwi = Kiwi()

    def extract_nouns(self, text: str) -> List[str]:
        tokens = self._kiwi.tokenize(text)
        return [token.form for token in tokens if str(token.tag) in _NOUN_TAGS]
