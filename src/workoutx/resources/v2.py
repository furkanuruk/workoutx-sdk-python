"""Access to /v2/* (API-key auth): the new exercise catalog with signed media links.

Media links expire (about 24 h after they are issued). Store exercise ids, not
media URLs, and call :meth:`V2Resource.fresh_media` when you display an exercise.

``lang`` ("en", "tr", "de", "es", "fr", "zh-SG", "zh-HK") translates names,
text, muscles and terms; filters always take the English values. Parameters
keep the API's camelCase names (``weightKg``, ``bodyFocus``, ``avoidJoints``,
``daysPerWeek``).
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

from .._http import HttpClient

_REFRESH_MARGIN_S = 5 * 60

# snake_case spellings that list() also accepts.
_LIST_ALIASES = {
    "body_part": "bodyPart",
    "joint_focus": "jointFocus",
    "intensity_level": "intensityLevel",
    "movement_tag": "movementTag",
}

# Workout params that take several values: a list or tuple is sent comma-separated.
_CSV_PARAMS = ("equipment", "bodyFocus", "avoidJoints", "exclude")


def _expires_at(media: Dict[str, Any]) -> float:
    return datetime.fromisoformat(media["expiresAt"].replace("Z", "+00:00")).timestamp()


def _csv(params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: ",".join(str(x) for x in v) if k in _CSV_PARAMS and isinstance(v, (list, tuple)) else v
        for k, v in params.items()
    }


class V2Resource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http
        self._media: Dict[str, Dict[str, Any]] = {}
        # /v2/workout/*: workout generator and multi-week programs on v2 exercises.
        self.workout = V2WorkoutResource(http, self._remember)
        # /v2/supplements/*: supplements, stacks and picks for a v2 exercise.
        self.supplements = V2SupplementsResource(http)

    def list(self, **filters: Any) -> Dict[str, Any]:
        """Search the catalog. Filters (all optional, case-insensitive): body_part/bodyPart,
        target, equipment, category, model ("male"/"female"), difficulty, mechanic,
        force, muscle, name, limit, offset, lang. Joint & Rehab filters (Growth, Scale,
        legacy Ultra): jointFocus/joint_focus, intensityLevel/intensity_level,
        movementTag/movement_tag."""
        query = {_LIST_ALIASES.get(k, k): v for k, v in filters.items()}
        page = self._http.request("/v2/exercises", query=query)
        for e in page.get("results", []):
            self._remember(e)
        return page

    def get(self, exercise_id: str, *, lang: Optional[str] = None) -> Dict[str, Any]:
        e = self._http.request(f"/v2/exercises/{quote(exercise_id)}", query={"lang": lang})
        self._remember(e)
        return e

    def similar(self, exercise_id: str, **params: Any) -> Dict[str, Any]:
        """Similar exercises, best first (all plans). Params: model ("male"/"female"/"any";
        default: the exercise's model), limit, offset, lang.

        Returns ``{exerciseId, model, total, limit, offset, results}``; each result is a
        full v2 exercise plus ``score``. Never contains the exercise or its other-model clip.
        """
        page = self._http.request(f"/v2/exercises/{quote(exercise_id)}/similar", query=params)
        for e in page.get("results", []):
            self._remember(e)
        return page

    def alternatives(self, exercise_id: str, **params: Any) -> Dict[str, Any]:
        """Same target muscle, different equipment, best first (all plans). Params:
        equipment (preferred, not a filter), excludeEquipment, model, limit, offset, lang.
        Returns the same ranked page as :meth:`similar`."""
        page = self._http.request(f"/v2/exercises/{quote(exercise_id)}/alternatives", query=params)
        for e in page.get("results", []):
            self._remember(e)
        return page

    def calories(self, exercise_id: str, **params: Any) -> Dict[str, Any]:
        """Estimated calories burned (all plans). Params: weightKg (default 70),
        minutes (default 10), lang."""
        return self._http.request(f"/v2/exercises/{quote(exercise_id)}/calories", query=params)

    def media(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Fresh signed links for one exercise."""
        res = self._http.request(f"/v2/exercises/{quote(exercise_id)}/media")
        media = res.get("media")
        if media:
            self._media[exercise_id] = media
        return media

    def fresh_media(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Links you can use now: cached ones until 5 minutes before expiry, else new ones.

        Exercises received from list, get, media, similar, alternatives,
        workout.generate (including warm-up and cool-down items) and
        workout.program (its ``exerciseLibrary``) are cached."""
        cached = self._media.get(exercise_id)
        if cached and _expires_at(cached) - time.time() > _REFRESH_MARGIN_S:
            return cached
        return self.media(exercise_id)

    def legacy(self, v1_id: str, *, lang: Optional[str] = None) -> Dict[str, Any]:
        """Map a v1 exercise id (e.g. "0025") to its v2 exercise."""
        return self._http.request(f"/v2/exercises/legacy/{quote(v1_id)}", query={"lang": lang})

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

    def _remember(self, e: Any) -> None:
        if isinstance(e, dict) and e.get("media"):
            self._media[e["id"]] = e["media"]


class V2WorkoutResource:
    """/v2/workout/*: sessions and multi-week programs built from movement patterns
    on v2 exercises.

    The media links of every full exercise in a result (session exercises, warm-up
    and cool-down items, a program's ``exerciseLibrary``) are kept for
    :meth:`V2Resource.fresh_media`. ``equipment``, ``bodyFocus``, ``avoidJoints`` and
    ``exclude`` take a comma-separated string or a list.
    """

    def __init__(self, http: HttpClient, remember: Callable[[Any], None]) -> None:
        self._http = http
        self._remember = remember

    def generate(self, **params: Any) -> Dict[str, Any]:
        """Generate one session (plan-gated: Growth, Scale, legacy Pro and Ultra).

        Params: goal (muscle_gain, strength, fat_loss, endurance, mobility,
        general_fitness), duration (15-120 minutes), level (beginner, intermediate,
        advanced), equipment (names, or a preset: "gym", "home", "bodyweight"), split
        (full_body, full_body_b, full_body_c, upper, upper_b, lower, lower_b, push,
        push_b, pull, pull_b, legs, legs_b, core, conditioning, mobility; v1's
        push_pull_legs and upper_lower still work), bodyFocus (overrides split),
        avoidJoints (knee, shoulder, lumbar_spine, elbow, wrist, hip, ankle), format
        (auto, straight, superset, circuit), exclude (v2 ids), seed, model
        ("male"/"female"), lang.

        Returns ``{goal, level, model, seed, split, format, targetDurationMinutes,
        estimatedDurationMinutes, equipment, avoidJoints?, circuit?, summary, warmup,
        exercises, cooldown, notes?}``. ``warmup`` is ``{minutes, rampUp?, items}`` and
        ``cooldown`` ``{minutes, items}``; each item is ``{durationSeconds, perSide,
        note, exercise}``. Each of ``exercises`` is ``{order, block, role, pattern,
        sets, rounds?, reps? | durationSeconds?, perSide, restSeconds, rir?, tempo?,
        load?, cue, rationale, note?, alternatives, exercise}``: blocks "C1"/"C2" are
        a superset, ``alternatives`` are light (``{id, name, equipment, model}``, no
        media). Every ``exercise`` is a full v2 exercise with media.
        """
        workout = self._http.request("/v2/workout/generate", query=_csv(params))
        for item in workout.get("exercises") or []:
            self._remember(item.get("exercise"))
        for part in ("warmup", "cooldown"):
            for item in (workout.get(part) or {}).get("items") or []:
                self._remember(item.get("exercise"))
        return workout

    def program(self, **params: Any) -> Dict[str, Any]:
        """Generate a multi-week program (plan-gated: Scale, legacy Ultra).

        Params: goal, level, weeks (2-16), daysPerWeek (2-6), duration (20-120 minutes
        per session), equipment, avoidJoints, format, seed, model ("male"/"female"),
        lang. Programs take no split, bodyFocus or exclude.

        Returns ``{goal, level, model, seed, weeks, daysPerWeek, sessionDurationMinutes,
        equipment, avoidJoints?, schedule, progressionModel, blocks, weeklyVolume,
        sessions, program, exerciseLibrary}``. ``sessions`` are the session templates
        (warm-up, cool-down and exercises with pattern, cue, rationale, alternatives);
        ``program`` is the weeks (``{week, block, phase, deload, guidance, days}``) with
        each day's prescriptions. Exercises in both are light references by
        ``exerciseId``; ``exerciseLibrary`` has each one once as a full v2 exercise
        with media.
        """
        program = self._http.request("/v2/workout/program", query=_csv(params))
        for exercise in program.get("exerciseLibrary") or []:
            self._remember(exercise)
        return program


class V2SupplementsResource:
    """/v2/supplements/* (plan-gated: Growth, Scale, legacy Pro and Ultra; ``stack``:
    Scale, legacy Ultra). Exercise lookups take v2 exercise ids. Informational
    content only, not medical advice."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(self, **params: Any) -> Dict[str, Any]:
        """Supplements, strongest evidence first. Params: category, goal, timing, evidence,
        search, limit (default: the whole list), offset.
        Returns ``{total, limit, offset, results, disclaimer}``."""
        return self._http.request("/v2/supplements", query=params)

    def filters(self) -> Dict[str, Any]:
        return self._http.request("/v2/supplements/filters")

    def get(self, supplement_id: str) -> Dict[str, Any]:
        return self._http.request(f"/v2/supplements/{quote(supplement_id)}")

    def for_exercise(self, exercise_id: str, **params: Any) -> Dict[str, Any]:
        """Supplements relevant to a v2 exercise (e.g. "ex_SAWOOH"). Params: limit
        (1-20, default 6), lang."""
        return self._http.request(f"/v2/supplements/exercise/{quote(exercise_id)}", query=params)

    def stack(self, **params: Any) -> Dict[str, Any]:
        """A goal-based stack with a timing guide (plan-gated: Scale, legacy Ultra).
        Params: goal (required), level ("essential"/"standard"/"comprehensive")."""
        return self._http.request("/v2/supplements/stack", query=params)
