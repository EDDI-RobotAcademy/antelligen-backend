from abc import ABC, abstractmethod
from typing import Optional

from app.domains.stock_theme.domain.entity.defense_stock import DefenseStock


class DefenseStockRepositoryPort(ABC):

    @abstractmethod
    async def upsert(self, stock: DefenseStock) -> DefenseStock:
        """종목코드(code) 기준으로 존재하면 갱신, 없으면 신규 저장"""
        pass

    @abstractmethod
    async def find_all(self) -> list[DefenseStock]:
        """등록된 모든 방산주를 반환한다"""
        pass

    @abstractmethod
    async def find_by_theme(self, theme: str) -> list[DefenseStock]:
        """특정 테마 키워드가 포함된 방산주를 반환한다"""
        pass

    @abstractmethod
    async def find_by_code(self, code: str) -> Optional[DefenseStock]:
        """종목코드로 단일 종목을 조회한다"""
        pass
