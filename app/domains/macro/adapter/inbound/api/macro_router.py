from fastapi import APIRouter

from app.common.response.base_response import BaseResponse
from app.domains.macro.adapter.outbound.cache.market_risk_snapshot_store import (
    get_market_risk_snapshot_store,
)
from app.domains.macro.application.response.market_risk_judgement_response import (
    MarketRiskJudgementResponse,
)

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/market-risk", response_model=BaseResponse[MarketRiskJudgementResponse])
async def get_market_risk_status():
    """거시 경제 리스크 판단 현황판.

    매일 새벽 1시 배치(`job_refresh_market_risk`)가 LLM 파이프라인을 한 번 돌려
    스냅샷을 갱신한다. 이 엔드포인트는 스냅샷을 즉시 반환하기 때문에 프론트 접속
    시마다 LLM 호출이 일어나지 않는다.
    """
    store = get_market_risk_snapshot_store()
    snapshot = store.get()

    if snapshot is None:
        print("[macro.router] ⚠ 스냅샷 미준비 — 준비 중 응답 반환")
        return BaseResponse.ok(
            data=MarketRiskJudgementResponse(
                reference_date=__import__("datetime").date.today(),
                status="UNKNOWN",
                reasons=[],
                contextual_status="UNKNOWN",
                contextual_reasons=[],
                baseline_status="UNKNOWN",
                baseline_reasons=[],
                reference_videos=[],
                note_available=False,
                fallback_message="매크로 엔진이 초기 스냅샷을 준비 중입니다. 잠시 후 다시 시도해 주세요.",
                updated_at=None,
            ),
            message="스냅샷 준비 중",
        )

    print(
        f"[macro.router] ✓ 캐시 히트 status={snapshot.response.status} "
        f"updated_at={snapshot.updated_at.isoformat()}"
    )
    return BaseResponse.ok(data=snapshot.response, message="시장 리스크 판단 완료")
