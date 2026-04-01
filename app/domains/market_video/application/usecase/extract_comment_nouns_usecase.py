from typing import Optional

from app.domains.market_video.application.port.noun_extractor_port import NounExtractorPort
from app.domains.market_video.application.port.video_comment_repository_port import VideoCommentRepositoryPort
from app.domains.market_video.application.response.noun_frequency_response import NounFrequencyItem, NounFrequencyResponse
from app.domains.market_video.domain.service.noun_frequency_service import NounFrequencyService, _DEFAULT_TOP_N

_MAX_TOP_N = 500


class ExtractCommentNounsUseCase:
    def __init__(
        self,
        comment_repository: VideoCommentRepositoryPort,
        noun_extractor: NounExtractorPort,
    ):
        self._repo = comment_repository
        self._extractor = noun_extractor

    async def execute(
        self,
        video_id: Optional[str] = None,
        top_n: int = _DEFAULT_TOP_N,
    ) -> NounFrequencyResponse:
        if video_id:
            comments = await self._repo.find_by_video_id(video_id)
        else:
            comments = await self._repo.find_all()

        all_nouns: list[str] = []
        for comment in comments:
            nouns = self._extractor.extract_nouns(comment.comment_text)
            all_nouns.extend(nouns)

        consolidated_nouns = NounFrequencyService.consolidate_synonyms(all_nouns)
        unique_noun_count = len(set(consolidated_nouns))
        frequency_list = NounFrequencyService.count_frequencies(consolidated_nouns, top_n=top_n)
        items = [NounFrequencyItem(noun=item["noun"], count=item["count"]) for item in frequency_list]

        return NounFrequencyResponse(
            total_comments=len(comments),
            total_nouns=len(all_nouns),
            unique_noun_count=unique_noun_count,
            top_n=top_n,
            items=items,
        )
