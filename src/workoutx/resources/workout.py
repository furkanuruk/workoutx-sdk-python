"""Access to /v1/workout/* (API-key auth)."""
from __future__ import annotations

from typing import Any, Dict

from .._http import HttpClient


class WorkoutResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def generate(self, **params: Any) -> Dict[str, Any]:
        """Generate a single workout (plan-gated: requires ``workoutGenerator``)."""
        return self._http.request("/v1/workout/generate", query=params)

    def program(self, **params: Any) -> Dict[str, Any]:
        """Generate a multi-week program (plan-gated: requires ``workoutPrograms``)."""
        return self._http.request("/v1/workout/program", query=params)
