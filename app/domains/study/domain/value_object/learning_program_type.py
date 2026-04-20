from enum import Enum


class LearningProgramType(str, Enum):
    BACK_TO_THE_BASIC = "BACK_TO_THE_BASIC"
    RHYTHM_SERIES = "RHYTHM_SERIES"
    OTHER = "OTHER"

    @classmethod
    def classify(cls, title: str, description: str) -> "LearningProgramType":
        haystack = f"{title or ''} {description or ''}".lower()
        if "back to the basic" in haystack:
            return cls.BACK_TO_THE_BASIC
        if "리듬" in haystack:
            return cls.RHYTHM_SERIES
        return cls.OTHER

    @classmethod
    def is_target(cls, program: "LearningProgramType") -> bool:
        return program in {cls.BACK_TO_THE_BASIC, cls.RHYTHM_SERIES}
