"""거시 경제 리스크 판단 결과의 메모리 캐시.

매일 새벽 1시 배치가 LLM 파이프라인을 돌려 최신 스냅샷을 저장하고,
그 사이의 모든 조회 요청은 저장된 스냅샷을 그대로 반환한다.
프로세스 재시작 시에는 lifespan 에서 bootstrap 으로 최초 1회 갱신한다.
"""

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.domains.macro.application.response.market_risk_judgement_response import (
    MarketRiskJudgementResponse,
)


@dataclass
class MarketRiskSnapshot:
    response: MarketRiskJudgementResponse
    updated_at: datetime


class MarketRiskSnapshotStore:
    def __init__(self) -> None:
        self._snapshot: Optional[MarketRiskSnapshot] = None
        self._lock = threading.RLock()

    def set(self, response: MarketRiskJudgementResponse, updated_at: datetime) -> None:
        with self._lock:
            # updated_at 을 response 에도 주입해 프론트가 마지막 갱신 시각을 볼 수 있게 한다.
            enriched = response.model_copy(update={"updated_at": updated_at})
            self._snapshot = MarketRiskSnapshot(response=enriched, updated_at=updated_at)

    def get(self) -> Optional[MarketRiskSnapshot]:
        with self._lock:
            return self._snapshot


_singleton: Optional[MarketRiskSnapshotStore] = None


def get_market_risk_snapshot_store() -> MarketRiskSnapshotStore:
    global _singleton
    if _singleton is None:
        _singleton = MarketRiskSnapshotStore()
    return _singleton
