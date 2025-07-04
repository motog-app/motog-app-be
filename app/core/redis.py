# app/core/redis.py
from redis.asyncio import Redis
from app.core.config import settings

redis_client: Redis = None

async def get_redis_client() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.REDIS_URL)
    return redis_client

async def is_email_resend_throttled(email: str) -> bool:
    client = await get_redis_client()
    key = f"email_resend_cooldown:{email}"
    # setnx returns 1 if the key was set (i.e., it didn't exist), 0 if it already existed
    # expire sets the expiration time
    # We use a pipeline to ensure atomicity of SETNX and EXPIRE
    pipe = client.pipeline()
    pipe.setnx(key, 1)
    pipe.expire(key, settings.EMAIL_RESEND_COOLDOWN_SECONDS)
    results = await pipe.execute()
    
    # If setnx returned 0, it means the key already existed, so it's throttled
    return results[0] == 0
