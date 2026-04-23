from abc import ABC, abstractmethod
from typing import Optional

from app.domains.company_profile.domain.entity.company_profile import CompanyProfile


class DartCompanyInfoPort(ABC):
    @abstractmethod
    async def fetch(self, corp_code: str) -> Optional[CompanyProfile]:
        pass
