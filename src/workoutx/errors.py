"""Exceptions raised by the WorkoutX SDK."""
from __future__ import annotations

from typing import Any, Optional


class WorkoutXError(Exception):
    """Raised for any non-2xx response from the WorkoutX API.

    The parsed response body (when JSON) is available on ``.body``, and the
    common fields the API returns (``error``, ``message``, ``tip``, ``docs``)
    are surfaced directly.
    """

    def __init__(
        self,
        *,
        status: int,
        path: str,
        body: Any,
        message: str,
        code: Optional[str] = None,
        tip: Optional[str] = None,
        docs: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.path = path
        self.body = body
        self.code = code
        self.tip = tip
        self.docs = docs

    @property
    def is_rate_limited(self) -> bool:
        return self.status == 429

    @property
    def is_auth_error(self) -> bool:
        return self.status in (401, 403)

    @property
    def is_not_found(self) -> bool:
        return self.status == 404


class WorkoutXConnectionError(Exception):
    """Raised when a transport/network failure prevents getting a response."""
