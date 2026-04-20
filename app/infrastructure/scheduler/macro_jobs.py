import logging
from datetime import datetime

from app.domains.macro.adapter.outbound.cache.market_risk_snapshot_store import (
    get_market_risk_snapshot_store,
)
from app.domains.macro.adapter.outbound.external.langchain_risk_judgement_adapter import (
    LangChainRiskJudgementAdapter,
)
from app.domains.macro.adapter.outbound.external.youtube_macro_video_client import (
    YoutubeMacroVideoClient,
)
from app.domains.macro.adapter.outbound.file.study_note_file_reader import StudyNoteFileReader
from app.domains.macro.application.usecase.judge_market_risk_usecase import (
    JudgeMarketRiskUseCase,
)
from app.infrastructure.config.settings import get_settings
from app.infrastructure.external.openai_responses_client import get_openai_responses_client

logger = logging.getLogger(__name__)


async def job_refresh_market_risk() -> None:
    """거시 경제 리스크 판단 스냅샷을 새로 계산해 메모리 캐시에 저장."""
    print("[macro.job] 거시 경제 리스크 판단 스냅샷 갱신 시작")
    settings = get_settings()
    try:
        note_reader = StudyNoteFileReader()
        video_client = YoutubeMacroVideoClient(api_key=settings.youtube_api_key)
        llm_adapter = LangChainRiskJudgementAdapter(client=get_openai_responses_client())

        response = await JudgeMarketRiskUseCase(
            note_port=note_reader,
            video_port=video_client,
            llm_port=llm_adapter,
        ).execute()

        get_market_risk_snapshot_store().set(response, updated_at=datetime.now())
        print(
            f"[macro.job] ✅ 스냅샷 갱신 완료 status={response.status} "
            f"reasons={len(response.reasons)}"
        )
    except Exception as exc:
        print(f"[macro.job] ❌ 스냅샷 갱신 실패: {exc}")
        logger.exception("[macro.job] 스냅샷 갱신 실패: %s", exc)
