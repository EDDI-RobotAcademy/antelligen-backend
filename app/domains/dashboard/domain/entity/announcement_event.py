from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class AnnouncementEventType(str, Enum):
    MERGER_ACQUISITION = "MERGER_ACQUISITION"        # 합병 / 인수 / 분할
    CONTRACT = "CONTRACT"                             # 계약 / MOU
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"           # CEO / 임원 교체
    ACCOUNTING_ISSUE = "ACCOUNTING_ISSUE"             # 회계 이슈 / 재무제표 정정
    REGULATORY = "REGULATORY"                         # 규제 / 소송 / 제재
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"                 # 신제품 / 신기술 출시
    CRISIS = "CRISIS"                                 # 리콜 / 상장폐지 / 거래정지 / 관리종목
    EARNINGS_RELEASE = "EARNINGS_RELEASE"             # 분기/연간 실적 발표 (8-K Item 2.02 / 사업·분기·반기보고서)
    DEBT_ISSUANCE = "DEBT_ISSUANCE"                   # 회사채 / 전환사채(CB) / 신주인수권부사채(BW)
    SHAREHOLDER_MEETING = "SHAREHOLDER_MEETING"       # 주주총회 결과 (8-K Item 5.07)
    REGULATION_FD = "REGULATION_FD"                   # Reg FD 공정공시 (8-K Item 7.01)
    ARTICLES_AMENDMENT = "ARTICLES_AMENDMENT"         # 정관·부속법 개정 (8-K Item 5.03)
    # ── 한국 공시 특화 (OKR 1 P1.5) ──────────────────────
    EARNINGS_GUIDANCE = "EARNINGS_GUIDANCE"           # 잠정실적 (정기실적 발표 전 가이드 — 한국 시장 특화)
    STOCK_SPLIT = "STOCK_SPLIT"                       # 액면분할
    TREASURY_STOCK = "TREASURY_STOCK"                 # 자기주식 취득·처분
    RIGHTS_OFFERING = "RIGHTS_OFFERING"               # 유상증자
    BONUS_ISSUE = "BONUS_ISSUE"                       # 무상증자 / 주식배당
    MAJOR_EVENT = "MAJOR_EVENT"                       # 기타 주요사항 (fallback)


@dataclass
class AnnouncementEvent:
    date: date
    type: AnnouncementEventType
    title: str
    source: str  # "dart" | "sec_edgar"
    url: str
    items_str: Optional[str] = None  # SEC 8-K raw Item 코드(예: "1.01,9.01"). DART는 None.
