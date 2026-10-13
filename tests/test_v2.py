from datetime import datetime, timedelta, timezone

import pytest

from workoutx import WorkoutX, WorkoutXError


def _in_hours(h: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=h)).isoformat().replace("+00:00", "Z")


def _media(tag: str, expires_at: str = None):
    return {
        "expiresAt": expires_at or _in_hours(24),
        "mediaVersion": 1,
        "watermarked": False,
        "mp4": f"https://media.test/m/v1/ex_AAAAAA/mp4-720.mp4?s={tag}",
        "poster": f"https://media.test/m/v1/ex_AAAAAA/poster.jpg?s={tag}",
    }


def test_list_sends_filters_and_key_header_only(mock_http):
    mock = mock_http({"json": {"total": 1, "limit": 10, "offset": 0, "results": [{"id": "ex_AAAAAA", "media": _media("a")}]}})
    wx = WorkoutX(api_key="wx_test")

    page = wx.v2.list(model="female", body_part="chest", limit=10)

    assert page["results"][0]["id"] == "ex_AAAAAA"
    assert mock.last.path == "/v2/exercises"
    assert mock.last.query == {"model": "female", "bodyPart": "chest", "limit": "10"}
    assert mock.last.headers["x-workoutx-key"] == "wx_test"
    assert "api-key" not in mock.last.url


def test_routes(mock_http):
    mock = mock_http(lambda req: {"json": {"id": "ex_AAAAAA", "media": _media("m")} if "/media" in req.url else {}})
    wx = WorkoutX(api_key="wx_test")
    wx.v2.get("ex_AAAAAA")
    assert mock.last.path == "/v2/exercises/ex_AAAAAA"
    wx.v2.media("ex_AAAAAA")
    assert mock.last.path == "/v2/exercises/ex_AAAAAA/media"
    wx.v2.legacy("0025")
    assert mock.last.path == "/v2/exercises/legacy/0025"
    wx.v2.body_parts()
    assert mock.last.path == "/v2/bodyParts"


def test_fresh_media_reuses_valid_links(mock_http):
    mock = mock_http({"json": {"total": 1, "limit": 10, "offset": 0, "results": [{"id": "ex_AAAAAA", "media": _media("list")}]}})
    wx = WorkoutX(api_key="wx_test")
    wx.v2.list()
    links = wx.v2.fresh_media("ex_AAAAAA")
    assert "s=list" in links["mp4"]
    assert len(mock.calls) == 1


def test_fresh_media_refreshes_expiring_links(mock_http):
    mock = mock_http(lambda req: {"json": {"id": "ex_AAAAAA", "media": _media("fresh")}} if "/media" in req.url
                     else {"json": {"id": "ex_AAAAAA", "media": _media("old", _in_hours(0.05))}})
    wx = WorkoutX(api_key="wx_test")
    wx.v2.get("ex_AAAAAA")
    links = wx.v2.fresh_media("ex_AAAAAA")
    assert "s=fresh" in links["mp4"]
    assert mock.last.path == "/v2/exercises/ex_AAAAAA/media"


def _exercise(exercise_id, tag):
    """A v2 exercise as the API returns it (only what the SDK reads), media tagged s=<tag>."""
    return {"id": exercise_id, "name": f"Exercise {exercise_id}", "media": _media(tag)}


def _slot(order, exercise_id, tag):
    return {"order": order, "sets": 4, "reps": "6-8", "restSeconds": 90, "exercise": _exercise(exercise_id, tag)}


def test_list_sends_lang_and_joint_rehab_filters(mock_http):
    mock = mock_http({"json": {"total": 0, "limit": 10, "offset": 0, "results": []}})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.list(jointFocus="knee", intensity_level="gentle", movement_tag="joint-friendly", lang="zh-HK")

    assert mock.last.path == "/v2/exercises"
    assert mock.last.query == {
        "jointFocus": "knee", "intensityLevel": "gentle", "movementTag": "joint-friendly", "lang": "zh-HK",
    }


def test_get_and_legacy_take_optional_lang(mock_http):
    mock = mock_http({"json": {}})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.get("ex_SAWOOH")
    assert mock.last.url == "https://api.workoutxapp.com/v2/exercises/ex_SAWOOH"
    wx.v2.get("ex_SAWOOH", lang="tr")
    assert mock.last.path == "/v2/exercises/ex_SAWOOH"
    assert mock.last.query == {"lang": "tr"}

    wx.v2.legacy("0025")
    assert mock.last.url == "https://api.workoutxapp.com/v2/exercises/legacy/0025"
    wx.v2.legacy("0025", lang="de")
    assert mock.last.path == "/v2/exercises/legacy/0025"
    assert mock.last.query == {"lang": "de"}


def test_similar_query_and_ranked_page(mock_http):
    mock = mock_http({"json": {
        "exerciseId": "ex_SAWOOH", "model": "any", "total": 42, "limit": 2, "offset": 4,
        "results": [dict(_exercise("ex_WOZL6H", "a"), score=95), dict(_exercise("ex_KK4RJV", "b"), score=80)],
    }})
    wx = WorkoutX(api_key="wx_test")

    page = wx.v2.similar("ex_SAWOOH", model="any", limit=2, offset=4, lang="fr")

    assert mock.last.path == "/v2/exercises/ex_SAWOOH/similar"
    assert mock.last.query == {"model": "any", "limit": "2", "offset": "4", "lang": "fr"}
    assert (page["exerciseId"], page["model"], page["total"]) == ("ex_SAWOOH", "any", 42)
    assert [(e["id"], e["score"]) for e in page["results"]] == [("ex_WOZL6H", 95), ("ex_KK4RJV", 80)]


def test_alternatives_query(mock_http):
    mock = mock_http({"json": {"exerciseId": "ex_SAWOOH", "model": "male", "total": 0, "limit": 5, "offset": 0, "results": []}})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.alternatives("ex_SAWOOH", equipment="dumbbell", excludeEquipment="barbell", model="male", limit=5, offset=0, lang="es")

    assert mock.last.path == "/v2/exercises/ex_SAWOOH/alternatives"
    assert mock.last.query == {
        "equipment": "dumbbell", "excludeEquipment": "barbell", "model": "male", "limit": "5", "offset": "0", "lang": "es",
    }


def test_calories_query_and_response(mock_http):
    mock = mock_http({"json": {
        "id": "ex_SAWOOH", "name": "Barbell Bench Press", "model": "male", "bodyPart": "Chest", "target": "Pectorals",
        "weightKg": 80, "minutes": 30, "met": 5, "baseKcalPerMin": 6.1, "kcalPerMin": 6.97, "totalKcal": 209.1,
        "note": "Estimate",
    }})
    wx = WorkoutX(api_key="wx_test")

    est = wx.v2.calories("ex_SAWOOH", weightKg=80, minutes=30, lang="es")

    assert mock.last.path == "/v2/exercises/ex_SAWOOH/calories"
    assert mock.last.query == {"weightKg": "80", "minutes": "30", "lang": "es"}
    assert (est["kcalPerMin"], est["totalKcal"]) == (6.97, 209.1)


def test_fresh_media_reuses_similar_and_alternatives_links(mock_http):
    def reply(req):
        exercise_id = "ex_WOZL6H" if req.path.endswith("/similar") else "ex_KK4RJV"
        return {"json": {"exerciseId": "ex_SAWOOH", "model": "male", "total": 1, "limit": 10, "offset": 0,
                         "results": [dict(_exercise(exercise_id, exercise_id), score=70)]}}

    mock = mock_http(reply)
    wx = WorkoutX(api_key="wx_test")

    wx.v2.similar("ex_SAWOOH")
    wx.v2.alternatives("ex_SAWOOH", model="female")

    assert "s=ex_WOZL6H" in wx.v2.fresh_media("ex_WOZL6H")["mp4"]
    assert "s=ex_KK4RJV" in wx.v2.fresh_media("ex_KK4RJV")["mp4"]
    assert len(mock.calls) == 2


def test_workout_generate_maps_params_and_joins_lists(mock_http):
    mock = mock_http({"json": {"seed": "abc123", "exercises": []}})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.workout.generate(
        goal="strength", duration=60, level="advanced", equipment=["barbell", "dumbbell"], split="push",
        bodyFocus=("chest", "triceps"), exclude=["ex_WOZL6H", "ex_KK4RJV"], seed="abc123", model="female", lang="de",
    )

    assert mock.last.path == "/v2/workout/generate"
    assert mock.last.query == {
        "goal": "strength", "duration": "60", "level": "advanced", "equipment": "barbell,dumbbell", "split": "push",
        "bodyFocus": "chest,triceps", "exclude": "ex_WOZL6H,ex_KK4RJV", "seed": "abc123", "model": "female", "lang": "de",
    }


def test_workout_generate_passes_strings_through_and_drops_none(mock_http):
    mock = mock_http({"json": {"exercises": []}})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.workout.generate(equipment="barbell,dumbbell", exclude="ex_SAWOOH", seed=None)
    assert mock.last.query == {"equipment": "barbell,dumbbell", "exclude": "ex_SAWOOH"}

    wx.v2.workout.generate()
    assert mock.last.url == "https://api.workoutxapp.com/v2/workout/generate"


def test_workout_program_maps_params(mock_http):
    mock = mock_http({"json": {"program": []}})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.workout.program(goal="strength", level="beginner", weeks=8, daysPerWeek=4, duration=50,
                          equipment=["barbell", "dumbbell"], model="male", lang="fr")

    assert mock.last.path == "/v2/workout/program"
    assert mock.last.query == {
        "goal": "strength", "level": "beginner", "weeks": "8", "daysPerWeek": "4", "duration": "50",
        "equipment": "barbell,dumbbell", "model": "male", "lang": "fr",
    }


def test_workout_results_fill_media_cache(mock_http):
    def reply(req):
        if req.path == "/v2/workout/generate":
            return {"json": {"seed": "s1", "warmup": [], "cooldown": [], "exercises": [_slot(1, "ex_SAWOOH", "gen")]}}
        return {"json": {"program": [{"week": 1, "days": [{"day": 1, "focus": "push", "exercises": [_slot(1, "ex_WOZL6H", "prog")]}]}]}}

    mock = mock_http(reply)
    wx = WorkoutX(api_key="wx_test")

    workout = wx.v2.workout.generate(goal="muscle_gain")
    program = wx.v2.workout.program(weeks=2)

    assert workout["seed"] == "s1"
    assert workout["exercises"][0]["exercise"]["id"] == "ex_SAWOOH"
    assert program["program"][0]["days"][0]["exercises"][0]["exercise"]["id"] == "ex_WOZL6H"
    assert "s=gen" in wx.v2.fresh_media("ex_SAWOOH")["mp4"]
    assert "s=prog" in wx.v2.fresh_media("ex_WOZL6H")["mp4"]
    assert len(mock.calls) == 2


def test_supplements_list(mock_http):
    mock = mock_http({"json": {
        "total": 1, "limit": 5, "offset": 0, "disclaimer": "Not medical advice.",
        "results": [{"id": "creatine-monohydrate", "name": "Creatine Monohydrate"}],
    }})
    wx = WorkoutX(api_key="wx_test")

    page = wx.v2.supplements.list(category="performance", goal="strength", timing="pre_workout",
                                  evidence="strong", search="creatine", limit=5, offset=0)

    assert mock.last.path == "/v2/supplements"
    assert mock.last.query == {
        "category": "performance", "goal": "strength", "timing": "pre_workout", "evidence": "strong",
        "search": "creatine", "limit": "5", "offset": "0",
    }
    assert page["results"][0]["id"] == "creatine-monohydrate"
    assert page["disclaimer"] == "Not medical advice."


def test_supplement_routes(mock_http):
    mock = mock_http({"json": {}})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.supplements.filters()
    assert mock.last.path == "/v2/supplements/filters"

    wx.v2.supplements.get("creatine monohydrate")
    assert mock.last.path == "/v2/supplements/creatine%20monohydrate"

    wx.v2.supplements.for_exercise("ex_SAWOOH", limit=3, lang="tr")
    assert mock.last.path == "/v2/supplements/exercise/ex_SAWOOH"
    assert mock.last.query == {"limit": "3", "lang": "tr"}

    wx.v2.supplements.stack(goal="muscle_gain", level="essential")
    assert mock.last.path == "/v2/supplements/stack"
    assert mock.last.query == {"goal": "muscle_gain", "level": "essential"}


def test_plan_gate_403_raises_workoutx_error(mock_http):
    def reply(req):
        feature, plan = (("supplementStacks", "scale") if req.path == "/v2/supplements/stack"
                         else ("workoutGenerator", "growth"))
        return {"status": 403, "reason": "Forbidden", "json": {
            "error": "Plan Upgrade Required", "message": "This feature requires a higher plan. Current plan: Starter.",
            "feature": feature, "requiredPlan": plan, "upgrade": "https://workoutxapp.com/dashboard.html#billing",
        }}

    mock = mock_http(reply)
    wx = WorkoutX(api_key="wx_test")

    with pytest.raises(WorkoutXError) as ei:
        wx.v2.workout.generate(goal="strength")
    err = ei.value
    assert (err.status, err.code, err.path) == (403, "Plan Upgrade Required", "/v2/workout/generate")
    assert err.is_auth_error
    assert err.body["feature"] == "workoutGenerator"
    assert err.body["requiredPlan"] == "growth"

    with pytest.raises(WorkoutXError) as ei:
        wx.v2.supplements.stack(goal="muscle_gain")
    assert ei.value.status == 403
    assert ei.value.body["requiredPlan"] == "scale"

    assert len(mock.calls) == 2  # a 403 is not retried
