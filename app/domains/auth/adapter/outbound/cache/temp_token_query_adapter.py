import json
from typing import Optional

import redis.asyncio as aioredis

from app.domains.auth.application.port.out.temp_token_query_port import TempTokenQueryPort, TempUserInfo

TEMP_TOKEN_KEY_PREFIX = "temp_token:"


class TempTokenQueryAdapter(TempTokenQueryPort):
    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def find_by_token(self, token: str) -> Optional[TempUserInfo]:
        raw = await self._redis.get(f"{TEMP_TOKEN_KEY_PREFIX}{token}")
        if not raw:
            return None
        parsed = json.loads(raw)
        return TempUserInfo(
            nickname=parsed.get("nickname"),
            email=parsed.get("email"),
        )
