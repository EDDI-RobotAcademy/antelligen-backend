from app.domains.stock.market_data.domain.entity.popular_stock_ticker import (
    PopularStockTicker,
)
from app.domains.stock.market_data.infrastructure.orm.popular_stock_ticker_orm import (
    PopularStockTickerOrm,
)


class PopularStockTickerMapper:

    @staticmethod
    def to_entity(orm: PopularStockTickerOrm) -> PopularStockTicker:
        return PopularStockTicker(
            ticker_id=orm.id,
            ticker=orm.ticker,
            region=orm.region,
            asset_type=orm.asset_type,
            added_at=orm.added_at,
        )
