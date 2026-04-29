import json
import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class SnsSignalResultCache:
    """ticker별 SnsSignalResult 캐시 (Redis 기반)"""

    _TTL_SECONDS = 600  # 10분

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    def _key(self, ticker: str) -> str:
        return f"sentiment:result:{ticker}"

    async def get(self, ticker: str) -> dict | None:
        """캐시 조회. miss 또는 Redis 오류 시 None 반환."""
        try:
            raw = await self._redis.get(self._key(ticker))
            return json.loads(raw) if raw else None
        except (aioredis.RedisError, json.JSONDecodeError) as e:
            logger.warning("[SnsSignalCache] 캐시 조회 실패 ticker=%s: %s", ticker, e)
            return None

    async def set(self, ticker: str, result_dict: dict) -> None:
        """캐시 저장. Redis 오류 시 무시하고 계속 진행."""
        try:
            await self._redis.setex(
                self._key(ticker),
                self._TTL_SECONDS,
                json.dumps(result_dict, ensure_ascii=False),
            )
        except (aioredis.RedisError, TypeError) as e:
            logger.warning("[SnsSignalCache] 캐시 저장 실패 ticker=%s: %s", ticker, e)
