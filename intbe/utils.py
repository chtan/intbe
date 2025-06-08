import redis
from django.conf import settings

redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,  # or another DB index
    decode_responses=True  # optional: for automatic string decode
)
