"""DailyBarMapper — ORM → Entity 변환 검증."""
from datetime import date

from app.domains.stock.market_data.infrastructure.mapper.daily_bar_mapper import (
    DailyBarMapper,
)
from app.domains.stock.market_data.infrastructure.orm.daily_bar_orm import DailyBarOrm


def test_to_entity_preserves_all_fields():
    orm = DailyBarOrm(
        id=42,
        ticker="AAPL",
        bar_date=date(2026, 4, 1),
        open=100.0,
        high=110.0,
        low=99.0,
        close=105.0,
        volume=12345,
        adj_close=104.5,
        source="yfinance",
        bars_data_version="yfinance:adjusted:2026-04-26",
    )

    entity = DailyBarMapper.to_entity(orm)

    assert entity.ticker == "AAPL"
    assert entity.bar_date == date(2026, 4, 1)
    assert entity.close == 105.0
    assert entity.adj_close == 104.5
    assert entity.source == "yfinance"
    assert entity.bars_data_version == "yfinance:adjusted:2026-04-26"
