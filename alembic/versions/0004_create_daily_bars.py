"""create daily_bars

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-26

종목 일봉 OHLCV 영구 적재 테이블.
- (ticker, bar_date) UK
- adj_close, source, bars_data_version 컬럼: corporate action 보정 + 데이터 일관성 추적
- ix_daily_bars_ticker_date_desc, ix_daily_bars_bar_date 인덱스: ±N일 윈도우 조회 최적화
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_bars",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("bar_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("adj_close", sa.Float(), nullable=True),
        sa.Column("source", sa.String(32), nullable=False, server_default="yfinance"),
        sa.Column("bars_data_version", sa.String(64), nullable=True),
        sa.UniqueConstraint(
            "ticker", "bar_date", name="uq_daily_bars_ticker_date"
        ),
    )
    op.create_index(
        "ix_daily_bars_ticker_date_desc",
        "daily_bars",
        ["ticker", "bar_date"],
    )
    op.create_index(
        "ix_daily_bars_bar_date",
        "daily_bars",
        ["bar_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_daily_bars_bar_date", table_name="daily_bars")
    op.drop_index("ix_daily_bars_ticker_date_desc", table_name="daily_bars")
    op.drop_table("daily_bars")
