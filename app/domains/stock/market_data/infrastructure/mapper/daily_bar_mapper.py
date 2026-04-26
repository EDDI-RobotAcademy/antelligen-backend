from app.domains.stock.market_data.domain.entity.daily_bar import DailyBar
from app.domains.stock.market_data.infrastructure.orm.daily_bar_orm import DailyBarOrm


class DailyBarMapper:

    @staticmethod
    def to_entity(orm: DailyBarOrm) -> DailyBar:
        return DailyBar(
            ticker=orm.ticker,
            bar_date=orm.bar_date,
            open=orm.open,
            high=orm.high,
            low=orm.low,
            close=orm.close,
            volume=orm.volume,
            adj_close=orm.adj_close,
            source=orm.source,
            bars_data_version=orm.bars_data_version,
        )
