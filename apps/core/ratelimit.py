from django.core.cache import cache


def client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")


def allow(key: str, limit: int, window: int) -> bool:
    """Fixed window counter: True while fewer than `limit` hits happened in `window` seconds."""
    cache_key = f"ratelimit:{key}"
    if cache.add(cache_key, 1, window):
        return True
    try:
        return cache.incr(cache_key) <= limit
    except ValueError:
        cache.set(cache_key, 1, window)
        return True
