import redis
import os
from loguru import logger

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")


def get_redis_connection() -> redis.Redis:
    """
    Создает и возвращает соединение с Redis.

    Returns:
        redis.Redis: Соединение с Redis
    """
    logger.debug(f"Creating Redis connection to {REDIS_HOST}:{REDIS_PORT}")
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )


def ping_redis() -> bool:
    """
    Проверяет доступность Redis.

    Returns:
        bool: True если Redis доступен, иначе False
    """
    try:
        client = get_redis_connection()
        result = client.ping()
        logger.info(f"Redis ping success: {result}")
        return result
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {str(e)}")
        return False


def clear_redis_cache(pattern: str = "*") -> int:
    """
    Очищает кэш Redis по заданному шаблону.

    Args:
        pattern: Шаблон ключей для удаления

    Returns:
        int: Количество удаленных ключей
    """
    client = get_redis_connection()
    keys = client.keys(pattern)
    count = 0
    if keys:
        count = client.delete(*keys)
        logger.info(f"Cleared {count} keys from Redis cache with pattern '{pattern}'")
    return count
