from app.domains.stock_theme.domain.entity.defense_stock import DefenseStock
from app.domains.stock_theme.infrastructure.orm.defense_stock_orm import DefenseStockOrm


class DefenseStockMapper:

    @staticmethod
    def to_orm(stock: DefenseStock) -> DefenseStockOrm:
        return DefenseStockOrm(
            name=stock.name,
            code=stock.code,
            themes=stock.themes,
        )

    @staticmethod
    def to_entity(orm: DefenseStockOrm) -> DefenseStock:
        return DefenseStock(
            db_id=orm.id,
            name=orm.name,
            code=orm.code,
            themes=orm.themes,
        )
