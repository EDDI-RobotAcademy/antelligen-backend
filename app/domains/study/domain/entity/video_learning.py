from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from app.domains.study.domain.value_object.investment_view import InvestmentView
from app.domains.study.domain.value_object.learning_program_type import LearningProgramType


@dataclass
class StockInsight:
    stock_name: str
    investment_view: InvestmentView
    key_claims: List[str] = field(default_factory=list)
    evidences: List[str] = field(default_factory=list)


@dataclass
class VideoLearning:
    video_id: str
    title: str
    channel_name: str
    channel_id: str
    published_at: datetime
    collected_at: datetime
    program_type: LearningProgramType
    summary: str
    stock_insights: List[StockInsight] = field(default_factory=list)
