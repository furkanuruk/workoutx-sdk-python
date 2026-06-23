"""Access to /v1/supplements/* (API-key auth)."""
from __future__ import annotations

from typing import Any, Dict
from urllib.parse import quote

from .._http import HttpClient


class SupplementsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, **params: Any) -> Dict[str, Any]:
        return self._http.request("/v1/supplements", query=params)

    def filters(self) -> Dict[str, Any]:
        return self._http.request("/v1/supplements/filters")

    def stack(self, **params: Any) -> Dict[str, Any]:
        """Build a recommended stack (plan-gated: requires ``supplementStacks``)."""
        return self._http.request("/v1/supplements/stack", query=params)

    def for_exercise(self, exercise_id: str) -> Dict[str, Any]:
        return self._http.request(f"/v1/supplements/exercise/{quote(exercise_id)}")

    def get(self, supplement_id: str) -> Dict[str, Any]:
        return self._http.request(f"/v1/supplements/{quote(supplement_id)}")
