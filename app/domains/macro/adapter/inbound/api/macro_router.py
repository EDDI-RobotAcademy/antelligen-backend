from fastapi import APIRouter

from app.common.response.base_response import BaseResponse
from app.domains.macro.adapter.outbound.external.langchain_risk_judgement_adapter import (
    LangChainRiskJudgementAdapter,
)
from app.domains.macro.adapter.outbound.external.youtube_macro_video_client import (
    YoutubeMacroVideoClient,
)
from app.domains.macro.adapter.outbound.file.study_note_file_reader import (
    StudyNoteFileReader,
)
from app.domains.macro.application.response.market_risk_judgement_response import (
    MarketRiskJudgementResponse,
)
from app.domains.macro.application.usecase.judge_market_risk_usecase import (
    JudgeMarketRiskUseCase,
)
from app.infrastructure.config.settings import get_settings
from app.infrastructure.external.openai_responses_client import get_openai_responses_client

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/market-risk", response_model=BaseResponse[MarketRiskJudgementResponse])
async def get_market_risk_status():
    print("[macro.router] GET /macro/market-risk 수신")
    settings = get_settings()

    note_reader = StudyNoteFileReader()
    video_client = YoutubeMacroVideoClient(api_key=settings.youtube_api_key)
    llm_adapter = LangChainRiskJudgementAdapter(client=get_openai_responses_client())

    result = await JudgeMarketRiskUseCase(
        note_port=note_reader,
        video_port=video_client,
        llm_port=llm_adapter,
    ).execute()

    print(
        f"[macro.router] 응답 준비 status={result.status} reasons={len(result.reasons)} "
        f"contextual={result.contextual_status}({len(result.contextual_reasons)}) "
        f"baseline={result.baseline_status}({len(result.baseline_reasons)}) "
        f"videos={len(result.reference_videos)}"
    )
    return BaseResponse.ok(data=result, message="시장 리스크 판단 완료")
