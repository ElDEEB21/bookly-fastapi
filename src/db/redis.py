import redis.asyncio as redis
from src.config import Config

ACCESS_JTI_EXPIRY = 3600
REFRESH_JTI_EXPIRY = 60 * 60 * 24 * 2

_client = None

def get_redis_client():
    global _client
    if _client is None:
        _client = redis.from_url(Config.REDIS_URL)
    return _client

async def add_jti_to_blocklist(jti: str, expiry: int = ACCESS_JTI_EXPIRY) -> None:
    client = get_redis_client()
    await client.set(name=jti, value="", ex=expiry)

async def token_in_blocklist(jti: str) -> bool:
    client = get_redis_client()
    value = await client.get(jti)
    return value is not None

async def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    client = get_redis_client()
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, window_seconds)
    return count <= limit