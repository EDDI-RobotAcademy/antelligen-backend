"""create popular_stock_tickers + seed top tickers

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-26

전역 인기/관심 종목 풀. user_watchlist(per-user)와 합집합으로 daily_bars 적재 universe 결정.
seed: KR 시총 top 10 + US 메가캡 8개.
"""
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_KR_SEED = [
    ("005930", "EQUITY"),
    ("000660", "EQUITY"),
    ("373220", "EQUITY"),
    ("207940", "EQUITY"),
    ("005380", "EQUITY"),
    ("000270", "EQUITY"),
    ("068270", "EQUITY"),
    ("005490", "EQUITY"),
    ("035420", "EQUITY"),
    ("055550", "EQUITY"),
]

_US_SEED = [
    ("AAPL", "EQUITY"),
    ("MSFT", "EQUITY"),
    ("NVDA", "EQUITY"),
    ("GOOGL", "EQUITY"),
    ("AMZN", "EQUITY"),
    ("META", "EQUITY"),
    ("TSLA", "EQUITY"),
    ("AVGO", "EQUITY"),
]

_BENCHMARK_SEED = [
    ("^GSPC", "US", "INDEX"),
    ("^KS11", "KR", "INDEX"),
]


def upgrade() -> None:
    op.create_table(
        "popular_stock_tickers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("region", sa.String(8), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("ticker", name="uq_popular_stock_tickers_ticker"),
    )
    op.create_index(
        "ix_popular_stock_tickers_region",
        "popular_stock_tickers",
        ["region"],
    )

    bind = op.get_bind()
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")
    rows = (
        [(t, "KR", a) for t, a in _KR_SEED]
        + [(t, "US", a) for t, a in _US_SEED]
        + list(_BENCHMARK_SEED)
    )
    for ticker, region, asset_type in rows:
        bind.execute(
            sa.text(
                "INSERT INTO popular_stock_tickers "
                "(ticker, region, asset_type, added_at) "
                "VALUES (:ticker, :region, :asset_type, :added_at) "
                "ON CONFLICT (ticker) DO NOTHING"
            ),
            {
                "ticker": ticker,
                "region": region,
                "asset_type": asset_type,
                "added_at": now,
            },
        )


def downgrade() -> None:
    op.drop_index(
        "ix_popular_stock_tickers_region", table_name="popular_stock_tickers"
    )
    op.drop_table("popular_stock_tickers")
