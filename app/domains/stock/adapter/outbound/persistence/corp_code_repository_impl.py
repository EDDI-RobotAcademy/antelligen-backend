import csv
from pathlib import Path
from typing import Optional

from app.domains.stock.application.port.corp_code_repository import CorpCodeRepository
from app.domains.stock.domain.entity.corp_code_mapping import CorpCodeMapping


class CorpCodeRepositoryImpl(CorpCodeRepository):
    """CSV 기반 종목코드-DART 고유번호 매핑 레포지토리"""

    def __init__(self, csv_path: Optional[Path] = None):
        self._csv_path = csv_path or self._default_path()
        self._cache: Optional[dict[str, CorpCodeMapping]] = None

    def _default_path(self) -> Path:
        return (
            Path(__file__).parent.parent.parent.parent
            / "infrastructure"
            / "data"
            / "corp_codes.csv"
        )

    async def find_by_ticker(self, ticker: str) -> Optional[CorpCodeMapping]:
        """종목코드로 DART 고유번호 매핑을 조회합니다."""
        if self._cache is None:
            self._load_cache()

        return self._cache.get(ticker)

    def _load_cache(self) -> None:
        """CSV 파일에서 매핑 데이터를 로드합니다."""
        self._cache = {}

        if not self._csv_path.exists():
            return

        with open(self._csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get("ticker", "").strip()
                corp_code = row.get("corp_code", "").strip()
                corp_name = row.get("corp_name", "").strip()

                if ticker and corp_code:
                    self._cache[ticker] = CorpCodeMapping(
                        ticker=ticker,
                        corp_code=corp_code,
                        corp_name=corp_name,
                    )
