from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DefenseStock:
    name: str
    code: str
    themes: list[str]
    db_id: Optional[int] = field(default=None)
