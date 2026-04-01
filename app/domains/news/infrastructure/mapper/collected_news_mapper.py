import hashlib

from app.domains.news.domain.entity.collected_news import CollectedNews
from app.domains.news.infrastructure.orm.collected_news_orm import CollectedNewsOrm


class CollectedNewsMapper:

    @staticmethod
    def to_orm(news: CollectedNews) -> CollectedNewsOrm:
        return CollectedNewsOrm(
            title=news.title,
            description=news.description,
            url=news.url,
            url_hash=hashlib.sha256(news.url.encode()).hexdigest(),
            published_at=news.published_at,
            keyword=news.keyword,
        )

    @staticmethod
    def to_entity(orm: CollectedNewsOrm) -> CollectedNews:
        return CollectedNews(
            news_id=orm.id,
            title=orm.title,
            description=orm.description,
            url=orm.url,
            published_at=orm.published_at,
            keyword=orm.keyword,
            collected_at=orm.collected_at,
        )
