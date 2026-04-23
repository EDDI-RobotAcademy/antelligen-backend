from abc import ABC, abstractmethod
from typing import Optional

from app.domains.company_profile.domain.entity.company_profile import CompanyProfile


class CompanyProfileCachePort(ABC):
    @abstractmethod
    async def get(self, stock_code: str) -> Optional[CompanyProfile]:
        pass

    @abstractmethod
    async def save(self, stock_code: str, profile: CompanyProfile, ttl_seconds: int) -> None:
        pass
