from dataclasses import dataclass


@dataclass
class CorpCodeMapping:
    """종목코드-DART 고유번호 매핑 도메인 엔티티"""
    ticker: str  # 종목코드 (예: "005930")
    corp_code: str  # DART 고유번호 8자리 (예: "00126380")
    corp_name: str  # 회사명 (예: "삼성전자")
