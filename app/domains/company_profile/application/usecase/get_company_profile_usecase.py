from typing import Optional

from app.domains.company_profile.application.port.out.company_profile_cache_port import (
    CompanyProfileCachePort,
)
from app.domains.company_profile.application.port.out.dart_company_info_port import (
    DartCompanyInfoPort,
)
from app.domains.company_profile.domain.entity.company_profile import CompanyProfile
from app.domains.disclosure.application.port.company_repository_port import CompanyRepositoryPort


CACHE_TTL_SECONDS = 86400


class GetCompanyProfileUseCase:
    def __init__(
        self,
        company_repository: CompanyRepositoryPort,
        dart_company_info: DartCompanyInfoPort,
        cache: CompanyProfileCachePort,
    ):
        self._company_repo = company_repository
        self._dart = dart_company_info
        self._cache = cache

    async def execute(self, ticker: str) -> Optional[CompanyProfile]:
        cached = await self._cache.get(ticker)
        if cached is not None:
            return cached

        company = await self._company_repo.find_by_stock_code(ticker)
        if company is None:
            return None

        profile = await self._dart.fetch(company.corp_code)
        if profile is None:
            return None

        await self._cache.save(ticker, profile, CACHE_TTL_SECONDS)
        return profile
