# redis_helpers.py
import json
import logging

import redis
import redis.exceptions

logger = logging.getLogger(__name__)

try:
    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    redis_client.ping()
except redis.exceptions.ConnectionError:
    logger.warning("Redis not available. Falling back to in-memory cache.")
    redis_client = None

# Fallback in-memory cache
_fallback_cache = {}


def set_task_status(task_id: str, data: dict, ttl_seconds: int = 3600):
    key = f"email_task:{task_id}"
    if redis_client:
        redis_client.set(key, json.dumps(data), ex=ttl_seconds)
    else:
        _fallback_cache[key] = data


def get_task_status(task_id: str):
    key = f"email_task:{task_id}"
    if redis_client:
        raw = redis_client.get(key)
        return json.loads(raw) if raw else None
    else:
        return _fallback_cache.get(key)


def update_task_status(task_id: str, new_data: dict):
    key = f"email_task:{task_id}"
    if redis_client:
        raw = redis_client.get(key)
        if raw:
            current = json.loads(raw)
            current.update(new_data)
            redis_client.set(key, json.dumps(current), ex=3600)
    else:
        if key in _fallback_cache:
            _fallback_cache[key].update(new_data)
