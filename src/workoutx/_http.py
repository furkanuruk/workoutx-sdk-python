"""Minimal, dependency-free HTTP client (stdlib urllib) with retry + backoff."""
from __future__ import annotations

import json
import random
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional

from .errors import WorkoutXError, WorkoutXConnectionError

Query = Dict[str, Any]


def _build_ssl_context() -> ssl.SSLContext:
    """Build a verifying SSL context.

    Prefer the ``certifi`` CA bundle when available (avoids the common
    "CERTIFICATE_VERIFY_FAILED" error on macOS Python.org builds that lack
    system root certs); otherwise fall back to the platform default.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


class HttpClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: Optional[str],
        get_bearer: Optional[Callable[[], Optional[str]]],
        timeout: float,
        max_retries: int,
        default_headers: Dict[str, str],
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._get_bearer = get_bearer
        self._timeout = timeout
        self._max_retries = max_retries
        self._default_headers = default_headers
        self._ssl_context = _build_ssl_context()

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        query: Optional[Query] = None,
        body: Any = None,
        auth: str = "key",  # "key" | "bearer"
        raw: bool = False,
    ) -> Any:
        url = self._build_url(path, query)
        headers = {
            "Accept": "*/*" if raw else "application/json",
            **self._default_headers,
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        if auth == "bearer":
            token = self._get_bearer() if self._get_bearer else None
            if not token:
                raise WorkoutXError(
                    status=401,
                    path=path,
                    body=None,
                    code="Unauthorized",
                    message=(
                        "Body-scan endpoints require authentication. Provide "
                        "scan_token or scan_email/scan_password when creating the client."
                    ),
                )
            headers["Authorization"] = f"Bearer {token}"
        elif self._api_key:
            headers["X-WorkoutX-Key"] = self._api_key

        last_exc: Optional[BaseException] = None
        for attempt in range(self._max_retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=self._timeout, context=self._ssl_context) as resp:
                    payload = resp.read()
                    return payload if raw else self._parse(payload)
            except urllib.error.HTTPError as e:
                status = e.code
                if (status == 429 or status >= 500) and attempt < self._max_retries:
                    retry_after = self._retry_after(e)
                    if self._is_retryable(e, retry_after):
                        time.sleep(retry_after or _backoff(attempt))
                        continue
                raise self._to_error(e, path)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_exc = e
                if attempt < self._max_retries:
                    time.sleep(_backoff(attempt))
                    continue
                raise WorkoutXConnectionError(f"Request to {path} failed: {e}") from e

        raise WorkoutXConnectionError(f"Request to {path} failed after retries.") from last_exc

    # ── helpers ──────────────────────────────────────────────────────────────
    def _build_url(self, path: str, query: Optional[Query]) -> str:
        url = self._base_url + path
        if query:
            clean = {k: v for k, v in query.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode({k: str(v) for k, v in clean.items()})
        return url

    @staticmethod
    def _parse(payload: bytes) -> Any:
        if not payload:
            return None
        text = payload.decode("utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    @staticmethod
    def _is_retryable(e: urllib.error.HTTPError, retry_after: Optional[float]) -> bool:
        # A 429 is only worth retrying when it is a per-minute rate limit. An
        # exhausted monthly quota (X-Quota-Exceeded: true) cannot succeed until
        # the quota resets — or never, on Free — and its Retry-After can be
        # weeks away, which we must not sleep through either.
        if e.headers and e.headers.get("X-Quota-Exceeded") == "true":
            return False
        return retry_after is None or retry_after <= _MAX_RETRY_AFTER_S

    @staticmethod
    def _retry_after(e: urllib.error.HTTPError) -> Optional[float]:
        h = e.headers.get("Retry-After") if e.headers else None
        if not h:
            return None
        try:
            return float(h)
        except ValueError:
            return None

    @staticmethod
    def _to_error(e: urllib.error.HTTPError, path: str) -> WorkoutXError:
        body: Any = None
        parsed: Dict[str, Any] = {}
        try:
            raw = e.read().decode("utf-8")
            if raw:
                try:
                    parsed = json.loads(raw)
                    body = parsed
                except json.JSONDecodeError:
                    body = raw
        except Exception:
            pass
        message = (
            parsed.get("message")
            or parsed.get("error")
            or f"{e.code} {e.reason} for {path}"
        )
        return WorkoutXError(
            status=e.code,
            path=path,
            body=body,
            message=str(message),
            code=parsed.get("error"),
            tip=parsed.get("tip"),
            docs=parsed.get("docs"),
        )


# Longest server-requested wait we will sleep through before retrying.
_MAX_RETRY_AFTER_S = 60.0


def _backoff(attempt: int) -> float:
    return min(2.0, 0.25 * (2 ** attempt)) + random.random() * 0.1
