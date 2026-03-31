from collections import Counter
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_analysis.application.port.out.market_context_port import MarketContextPort
from app.domains.market_analysis.domain.service.context_builder import KeywordItem, StockThemeItem
from app.domains.market_video.infrastructure.orm.video_comment_orm import VideoCommentOrm
from app.domains.stock_theme.infrastructure.orm.stock_theme_orm import StockThemeOrm

_STOP_WORDS = {"있다", "없다", "하다", "이다", "되다", "것", "수", "등", "및", "그", "이", "저", "를", "을", "은", "는"}


class MarketContextRepositoryImpl(MarketContextPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_top_keywords(self, top_n: int) -> List[KeywordItem]:
        stmt = select(VideoCommentOrm.content).order_by(VideoCommentOrm.published_at.desc()).limit(200)
        result = await self._db.execute(stmt)
        contents = result.scalars().all()

        try:
            from kiwipiepy import Kiwi
            kiwi = Kiwi()
            counter: Counter = Counter()
            for content in contents:
                tokens = kiwi.tokenize(content)
                for token in tokens:
                    if token.tag in ("NNG", "NNP") and len(token.form) >= 2 and token.form not in _STOP_WORDS:
                        counter[token.form] += 1
            return [KeywordItem(keyword=word, count=cnt) for word, cnt in counter.most_common(top_n)]
        except Exception:
            return []

    async def get_stock_themes(self) -> List[StockThemeItem]:
        stmt = select(StockThemeOrm)
        result = await self._db.execute(stmt)
        orm_list = result.scalars().all()
        return [
            StockThemeItem(name=orm.name, code=orm.code, themes=orm.themes or [])
            for orm in orm_list
        ]
