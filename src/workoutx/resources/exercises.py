"""Access to /v1/exercises/* (API-key auth)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .._http import HttpClient
from ..errors import WorkoutXError


class ExercisesResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, *, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        return self._http.request("/v1/exercises", query={"limit": limit, "offset": offset})

    def get(self, exercise_id: str) -> Dict[str, Any]:
        """Look up a single exercise by exact numeric ID (e.g. "0001").

        IDs are not sequential. To resolve a human name use :meth:`by_name`,
        or :meth:`find` which tries an ID then falls back to a name search.
        """
        return self._http.request(f"/v1/exercises/{quote(exercise_id)}")

    def by_name(self, name: str, *, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._http.request(
            f"/v1/exercises/name/{quote(name)}", query={"limit": limit, "offset": offset}
        )

    def by_body_part(self, body_part: str, **params: Any) -> Dict[str, Any]:
        return self._http.request(f"/v1/exercises/bodyPart/{quote(body_part)}", query=params)

    def by_target(self, target: str, **params: Any) -> Dict[str, Any]:
        return self._http.request(f"/v1/exercises/target/{quote(target)}", query=params)

    def by_equipment(self, equipment: str, **params: Any) -> Dict[str, Any]:
        return self._http.request(f"/v1/exercises/equipment/{quote(equipment)}", query=params)

    def search(self, **params: Any) -> Dict[str, Any]:
        """Multi-filter search (plan-gated: requires the ``multiFilter`` feature)."""
        return self._http.request("/v1/exercises/search", query=params)

    def similar(self, exercise_id: str, **params: Any) -> Dict[str, Any]:
        return self._http.request(f"/v1/exercises/{quote(exercise_id)}/similar", query=params)

    def alternatives(self, exercise_id: str, **params: Any) -> Dict[str, Any]:
        return self._http.request(f"/v1/exercises/{quote(exercise_id)}/alternatives", query=params)

    def calories(self, exercise_id: str, **params: Any) -> Dict[str, Any]:
        return self._http.request(f"/v1/exercises/{quote(exercise_id)}/calories", query=params)

    def changes(self, **params: Any) -> Dict[str, Any]:
        return self._http.request("/v1/exercises/changes", query=params)

    def body_part_list(self) -> List[str]:
        return self._http.request("/v1/exercises/bodyPartList")

    def target_list(self) -> List[str]:
        return self._http.request("/v1/exercises/targetList")

    def equipment_list(self) -> List[str]:
        return self._http.request("/v1/exercises/equipmentList")

    def secondary_muscle_list(self) -> List[str]:
        return self._http.request("/v1/exercises/secondaryMuscleList")

    def find(self, id_or_name: str) -> Optional[Dict[str, Any]]:
        """Try an ID first; on 404 fall back to a name search. Returns None if neither matches."""
        try:
            return self.get(id_or_name)
        except WorkoutXError as e:
            if not e.is_not_found:
                raise
        matches = self.by_name(id_or_name, limit=1)
        return matches[0] if matches else None
