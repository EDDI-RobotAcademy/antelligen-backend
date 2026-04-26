from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class AnnouncementEventType(str, Enum):
    MERGER_ACQUISITION = "MERGER_ACQUISITION"        # 합병 / 인수
    CONTRACT = "CONTRACT"                             # 계약 / MOU
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"           # CEO / 임원 교체
    ACCOUNTING_ISSUE = "ACCOUNTING_ISSUE"             # 회계 이슈 / 재무제표 정정
    REGULATORY = "REGULATORY"                         # 규제 / 소송 / 제재
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"                 # 신제품 / 신기술 출시
    CRISIS = "CRISIS"                                 # 리콜 / 상장폐지 / 거래정지
    EARNINGS_RELEASE = "EARNINGS_RELEASE"             # 분기/연간 실적 발표 (8-K Item 2.02)
    DEBT_ISSUANCE = "DEBT_ISSUANCE"                   # 회사채 발행 / 자본 조달
    SHAREHOLDER_MEETING = "SHAREHOLDER_MEETING"       # 주주총회 결과 (8-K Item 5.07)
    REGULATION_FD = "REGULATION_FD"                   # Reg FD 공정공시 (8-K Item 7.01)
    ARTICLES_AMENDMENT = "ARTICLES_AMENDMENT"         # 정관·부속법 개정 (8-K Item 5.03)
    MAJOR_EVENT = "MAJOR_EVENT"                       # 기타 주요사항 (fallback)


@dataclass
class AnnouncementEvent:
    date: date
    type: AnnouncementEventType
    title: str
    source: str  # "dart" | "sec_edgar"
    url: str
    items_str: Optional[str] = None  # SEC 8-K raw Item 코드(예: "1.01,9.01"). DART는 None.
