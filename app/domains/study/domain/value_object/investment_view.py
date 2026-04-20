from enum import Enum


class InvestmentView(str, Enum):
    BUY = "매수"
    HOLD = "관망"
    SELL = "매도"
    WATCH = "지켜보기"
    UNKNOWN = "불명"

    @classmethod
    def parse(cls, raw: str) -> "InvestmentView":
        if not raw:
            return cls.UNKNOWN
        normalized = raw.strip()
        for member in cls:
            if member.value == normalized:
                return member
        mapping = {
            "buy": cls.BUY,
            "hold": cls.HOLD,
            "sell": cls.SELL,
            "watch": cls.WATCH,
        }
        return mapping.get(normalized.lower(), cls.UNKNOWN)
