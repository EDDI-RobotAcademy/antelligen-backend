from fastapi import APIRouter

from app.common.response.base_response import BaseResponse
from app.domains.study.adapter.outbound.external.openai_video_learning_adapter import (
    OpenAIVideoLearningAdapter,
)
from app.domains.study.adapter.outbound.external.youtube_transcript_api_client import (
    YoutubeTranscriptApiClient,
)
from app.domains.study.adapter.outbound.external.youtube_video_source_client import (
    YoutubeVideoSourceClient,
)
from app.domains.study.adapter.outbound.file.study_note_file_reader import (
    StudyNoteFileReader,
)
from app.domains.study.adapter.outbound.file.study_note_file_writer import (
    StudyNoteFileWriter,
)
from app.domains.study.application.request.learn_study_request import LearnStudyRequest
from app.domains.study.application.response.learn_study_response import LearnStudyResponse
from app.domains.study.application.usecase.learn_study_videos_usecase import (
    LearnStudyVideosUseCase,
)
from app.infrastructure.config.settings import get_settings
from app.infrastructure.external.openai_responses_client import get_openai_responses_client

router = APIRouter(prefix="/study", tags=["study"])


@router.post("/learn", response_model=BaseResponse[LearnStudyResponse])
async def learn_study_videos(request: LearnStudyRequest):
    print(f"[study.router] POST /study/learn 수신 request={request.model_dump()}")
    settings = get_settings()

    video_source = YoutubeVideoSourceClient(api_key=settings.youtube_api_key)
    transcript_client = YoutubeTranscriptApiClient()
    llm_adapter = OpenAIVideoLearningAdapter(client=get_openai_responses_client())
    note_reader = StudyNoteFileReader()
    note_writer = StudyNoteFileWriter()

    result = await LearnStudyVideosUseCase(
        video_source_port=video_source,
        transcript_port=transcript_client,
        llm_port=llm_adapter,
        note_reader_port=note_reader,
        note_writer_port=note_writer,
    ).execute(request)

    print(
        f"[study.router] 응답 준비 processed={result.processed_count} "
        f"file_path={result.file_path or '(없음)'}"
    )
    return BaseResponse.ok(data=result, message=result.message or "학습 완료")
