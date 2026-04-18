from dataclasses import dataclass, field
from datetime import date
from typing import List

from app.domains.macro.domain.entity.macro_reference_video import MacroReferenceVideo
from app.domains.macro.domain.value_object.risk_status import RiskStatus


@dataclass
class MarketRiskJudgement:
    reference_date: date
    status: RiskStatus
    reasons: List[str]
    reference_videos: List[MacroReferenceVideo] = field(default_factory=list)
    note_available: bool = False
    fallback_message: str = ""
