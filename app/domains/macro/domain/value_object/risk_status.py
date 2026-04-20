from enum import Enum


class RiskStatus(str, Enum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def parse(cls, raw: str) -> "RiskStatus":
        if raw is None:
            return cls.UNKNOWN
        normalized = raw.strip().upper().replace("-", "_").replace(" ", "_")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.UNKNOWN
