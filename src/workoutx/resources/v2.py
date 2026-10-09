"""Access to /v2/* (API-key auth): the new exercise catalog with signed media links.

Media links expire (about 24 h after they are issued). Store exercise ids, not
media URLs, and call :meth:`V2Resource.fresh_media` when you display an exercise.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .._http import HttpClient

_REFRESH_MARGIN_S = 5 * 60


def _expires_at(media: Dict[str, Any]) -> float:
    return datetime.fromisoformat(media["expiresAt"].replace("Z", "+00:00")).timestamp()


class V2Resource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self._media: Dict[str, Dict[str, Any]] = {}

    def list(self, **filters: Any) -> Dict[str, Any]:
        """Search the catalog. Filters (all optional, case-insensitive): body_part/bodyPart,
        target, equipment, category, model ("male"/"female"), difficulty, mechanic,
        force, muscle, name, limit, offset."""
        query = {("bodyPart" if k == "body_part" else k): v for k, v in filters.items()}
        page = self._http.request("/v2/exercises", query=query)
        for e in page.get("results", []):
            self._remember(e)
        return page

    def get(self, exercise_id: str) -> Dict[str, Any]:
        e = self._http.request(f"/v2/exercises/{quote(exercise_id)}")
        self._remember(e)
        return e

    def media(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Fresh signed links for one exercise."""
        res = self._http.request(f"/v2/exercises/{quote(exercise_id)}/media")
        media = res.get("media")
        if media:
            self._media[exercise_id] = media
        return media

    def fresh_media(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Links you can use now: cached ones until 5 minutes before expiry, else new ones."""
        cached = self._media.get(exercise_id)
        if cached and _expires_at(cached) - time.time() > _REFRESH_MARGIN_S:
            return cached
        return self.media(exercise_id)

    def legacy(self, v1_id: str) -> Dict[str, Any]:
        """Map a v1 exercise id (e.g. "0025") to its v2 exercise."""
        return self._http.request(f"/v2/exercises/legacy/{quote(v1_id)}")

    def body_parts(self) -> List[Dict[str, Any]]:
        return self._http.request("/v2/bodyParts")

    def targets(self) -> List[Dict[str, Any]]:
        return self._http.request("/v2/targets")

    def equipment(self) -> List[Dict[str, Any]]:
        return self._http.request("/v2/equipment")

    def categories(self) -> List[Dict[str, Any]]:
        return self._http.request("/v2/categories")

    def muscles(self) -> List[Dict[str, Any]]:
        return self._http.request("/v2/muscles")

    def _remember(self, e: Dict[str, Any]) -> None:
        if isinstance(e, dict) and e.get("media"):
            self._media[e["id"]] = e["media"]
