import hashlib
import json
import logging
import time
from typing import Any

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_BACKOFF = 2.0


class ServiceError(Exception):
    """Raised when a remote open data service is unreachable or answers with an error."""


class JsonClient:
    def __init__(
        self,
        base_url: str,
        *,
        headers: dict | None = None,
        retries: int = 2,
        cache_ttl: int = 3600,
        backoff: float = 0.5,
    ):
        conf = settings.INTEGRATIONS
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self.cache_ttl = cache_ttl
        self.backoff = backoff
        self.headers = {"User-Agent": conf["USER_AGENT"], "Accept": "application/json"}
        self.headers.update(headers or {})
        self.timeout = conf["TIMEOUT"]

    def _cache_key(self, path: str, params: dict | None) -> str:
        raw = json.dumps([self.base_url, path, params or {}], sort_keys=True, default=str)
        return "integrations:" + hashlib.sha256(raw.encode()).hexdigest()

    def get(self, path: str, params: dict | None = None, *, cache_ttl: int | None = None) -> Any:
        ttl = self.cache_ttl if cache_ttl is None else cache_ttl
        key = self._cache_key(path, params)
        if ttl and (cached := cache.get(key)) is not None:
            return cached

        data = self._request(path, params)
        if ttl:
            cache.set(key, data, ttl)
        return data

    def _request(self, path: str, params: dict | None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        error: Exception | None = None
        for attempt in range(self.retries + 1):
            if attempt:
                time.sleep(min(self.backoff * 2 ** (attempt - 1), MAX_BACKOFF))
            try:
                response = httpx.get(url, params=params, headers=self.headers, timeout=self.timeout)
            except httpx.HTTPError as exc:
                error = exc
                continue
            if response.status_code in RETRY_STATUSES:
                error = ServiceError(f"{url} answered {response.status_code}")
                continue
            if response.status_code == 404:
                return None
            if response.is_error:
                raise ServiceError(f"{url} answered {response.status_code}")
            try:
                return response.json()
            except ValueError as exc:
                raise ServiceError(f"{url} returned invalid JSON") from exc

        logger.warning("Open data request failed: %s (%s)", url, error)
        raise ServiceError(str(error)) from error
