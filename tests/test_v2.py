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


def _exercise(exercise_id, tag, name=None):
    """A v2 exercise as the API returns it (only what the SDK reads), media tagged s=<tag>."""
    return {"id": exercise_id, "name": name or f"Exercise {exercise_id}", "media": _media(tag)}


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


def _session_response():
    """A session as /v2/workout/generate returns it, modeled on a real response.
    Exercises are trimmed to what the SDK reads; media tagged s=<tag>."""
    return {
        "goal": "muscle_gain", "level": "intermediate", "model": "female", "seed": "doc1", "split": "full_body",
        "format": "superset", "targetDurationMinutes": 45, "estimatedDurationMinutes": 41,
        "equipment": ["bench", "body weight", "dumbbell"], "avoidJoints": ["knee"],
        "summary": {
            "totalExercises": 3, "workingSets": 9, "patterns": ["squat", "hinge", "push_vertical"],
            "muscles": [{"group": "Quads", "sets": 4.5}, {"group": "Glutes", "sets": 4.5}, {"group": "Hamstrings", "sets": 3}],
        },
        "warmup": {
            "minutes": 6,
            "rampUp": "Before Dumbbell Front Squat: 2 ramp-up sets at about 50% × 10 and 75% × 5 of your working weight.",
            "items": [
                {"durationSeconds": 240, "perSide": False, "note": "Easy pace: raise your heart rate and body temperature.",
                 "exercise": _exercise("ex_L4EMF6", "warm", "Walking")},
                {"durationSeconds": 40, "perSide": False, "note": "Controlled, full range of motion.",
                 "exercise": _exercise("ex_UBH37I", "warm2", "Lying on Side Arm Circle Warm Up")},
            ],
        },
        "exercises": [
            {
                "order": 1, "block": "A", "role": "main", "pattern": "squat", "sets": 3, "reps": "6-8", "perSide": False,
                "restSeconds": 120, "rir": 2, "tempo": "3-0-1-0", "load": "70–80% of 1RM",
                "cue": "Ensure your elbows stay up and forward to keep the dumbbells stable on your shoulders.",
                "rationale": "Main lift: squat for the quadriceps and glutes.",
                "note": "Joint care: use a pain-free range and a load you control easily.",
                "alternatives": [
                    {"id": "ex_O6QQUL", "name": "Bodyweight Full Squat With Overhead Press", "equipment": "Body Weight", "model": "male"},
                    {"id": "ex_KNIBLJ", "name": "Bodyweight Squat", "equipment": "Body Weight", "model": "male"},
                ],
                "exercise": _exercise("ex_TFXRNX", "main", "Dumbbell Front Squat"),
            },
            {
                "order": 2, "block": "B1", "role": "secondary", "pattern": "hinge", "sets": 3, "reps": "8-10",
                "perSide": False, "restSeconds": 60, "rir": 2, "tempo": "3-0-1-0",
                "cue": "Focus on hinging at the hips rather than bending at the waist.",
                "rationale": "Secondary lift: hip hinge for the hamstrings and glutes.",
                "alternatives": [{"id": "ex_JUDO37", "name": "Bodyweight Hip Thrust", "equipment": "Body Weight", "model": "female"}],
                "exercise": _exercise("ex_UA3FUQ", "b1", "Dumbbell Romanian Deadlift"),
            },
            {
                "order": 3, "block": "B2", "role": "secondary", "pattern": "push_vertical", "sets": 3, "reps": "8-10",
                "perSide": False, "restSeconds": 90, "rir": 2, "cue": None,
                "rationale": "Secondary lift: overhead press for the shoulders.", "alternatives": [],
                "exercise": _exercise("ex_DSOP01", "b2", "Dumbbell Seated Shoulder Press"),
            },
        ],
        "cooldown": {
            "minutes": 2,
            "items": [
                {"durationSeconds": 30, "perSide": True, "note": "Stretch for the quads; breathe slowly, no bouncing.",
                 "exercise": _exercise("ex_CWLQWA", "cool", "Standing Quadriceps Stretch")},
            ],
        },
        "notes": ["Joint care for knee: high-stress movements are left out and moderate ones use lighter loads and "
                  "higher reps. This is general guidance, not medical advice."],
    }


def _program_response():
    """A program as /v2/workout/program returns it, modeled on a real response."""
    def day(rir, deload=False):
        squat = {"order": 1, "block": "A", "role": "main", "exerciseId": "ex_NEMYLA", "name": "Barbell Full Squat",
                 "sets": 2 if deload else 3, "perSide": False, "restSeconds": 120, "reps": "6-8", "rir": rir,
                 "load": "About 60% of your usual working weight" if deload else "70–80% of 1RM", "tempo": "3-0-1-0"}
        if deload:
            squat["note"] = "Deload: lighter and fewer sets. Leave the gym feeling fresh."
        bench = {"order": 2, "block": "B", "role": "main", "exerciseId": "ex_SAWOOH", "name": "Barbell Bench Press",
                 "sets": 2 if deload else 3, "perSide": False, "restSeconds": 120, "reps": "6-8", "rir": rir,
                 "load": "70–80% of 1RM", "tempo": "3-0-1-0"}
        return {"day": 1, "weekday": "Monday", "session": "A", "name": "Full body A", "exercises": [squat, bench]}

    return {
        "goal": "muscle_gain", "level": "intermediate", "model": "male", "seed": "doc2", "weeks": 6, "daysPerWeek": 3,
        "sessionDurationMinutes": 60, "equipment": ["any"],
        "schedule": [
            {"day": 1, "weekday": "Monday", "session": "A", "name": "Full body A"},
            {"day": 2, "weekday": "Wednesday", "session": "B", "name": "Full body B"},
            {"day": 3, "weekday": "Friday", "session": "C", "name": "Full body C"},
        ],
        "progressionModel": {
            "name": "Double progression with rising effort",
            "summary": "Each block starts about 3 reps short of failure and gets closer every week. A deload week ends each block.",
            "rule": "When you reach the top of the rep range on every set, add 2.5–5% load next session and work back up the range.",
            "deloadEvery": 5,
        },
        "blocks": [
            {"block": 1, "weeks": [1, 2, 3, 4, 5], "focus": "Foundation", "deloadWeek": 5},
            {"block": 2, "weeks": [6], "focus": "Progression"},
        ],
        "weeklyVolume": [
            {"group": "Chest", "sets": 13.5, "target": [10, 16], "status": "ok"},
            {"group": "Triceps", "sets": 9, "target": [10, 16], "status": "low"},
        ],
        "sessions": [{
            "session": "A", "name": "Full body A", "split": "full_body", "goal": "muscle_gain", "format": "superset",
            "estimatedDurationMinutes": 57,
            "warmup": {
                "minutes": 6,
                "rampUp": "Before Barbell Full Squat: 2 ramp-up sets at about 50% × 10 and 75% × 5 of your working weight.",
                "items": [{"exerciseId": "ex_YOPLC7", "name": "Treadmill Walk", "durationSeconds": 240, "perSide": False,
                           "note": "Easy pace: raise your heart rate and body temperature."}],
            },
            "cooldown": {
                "minutes": 2,
                "items": [{"exerciseId": "ex_5P2L5F", "name": "Fixed Bar Stretch", "durationSeconds": 30, "perSide": False,
                           "note": "Stretch for the shoulders; breathe slowly, no bouncing."}],
            },
            "exercises": [
                {"order": 1, "block": "A", "role": "main", "pattern": "squat", "exerciseId": "ex_NEMYLA",
                 "name": "Barbell Full Squat", "cue": "Keep your chest up and back straight to maintain proper posture and alignment.",
                 "rationale": "Main lift: squat for the quadriceps and glutes.",
                 "alternatives": [{"id": "ex_NN32EP", "name": "Cable Goblet Squat", "equipment": "Cable", "model": "male"}]},
                {"order": 2, "block": "B", "role": "main", "pattern": "push_horizontal", "exerciseId": "ex_SAWOOH",
                 "name": "Barbell Bench Press", "cue": "Keep your feet flat on the floor to maintain stability and support your lower back.",
                 "rationale": "Main lift: horizontal press for the chest.",
                 "alternatives": [{"id": "ex_WOZL6H", "name": "Push Ups Bodyweight", "equipment": "Body Weight", "model": "male"}]},
            ],
        }],
        "program": [
            {"week": 1, "block": 1, "phase": "accumulation", "deload": False,
             "guidance": "First week of the block: leave a few reps in reserve and focus on technique.", "days": [day(3)]},
            {"week": 5, "block": 1, "phase": "deload", "deload": True,
             "guidance": "Deload week: lighter loads and fewer sets so you start the next block fresh.", "days": [day(4, True)]},
        ],
        "exerciseLibrary": [
            _exercise("ex_NEMYLA", "lib-squat", "Barbell Full Squat"),
            _exercise("ex_SAWOOH", "lib-bench", "Barbell Bench Press"),
            _exercise("ex_YOPLC7", "lib-walk", "Treadmill Walk"),
            _exercise("ex_5P2L5F", "lib-stretch", "Fixed Bar Stretch"),
        ],
    }


def test_workout_generate_maps_params_and_joins_lists(mock_http):
    mock = mock_http({"json": _session_response()})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.workout.generate(
        goal="general_fitness", duration=15, level="advanced", equipment=["dumbbell", "bench"], split="full_body_b",
        bodyFocus=("chest", "triceps"), avoidJoints=["knee", "lumbar_spine"], format="superset",
        exclude=["ex_WOZL6H", "ex_KK4RJV"], seed="abc123", model="female", lang="de",
    )

    assert mock.last.path == "/v2/workout/generate"
    assert mock.last.query == {
        "goal": "general_fitness", "duration": "15", "level": "advanced", "equipment": "dumbbell,bench",
        "split": "full_body_b", "bodyFocus": "chest,triceps", "avoidJoints": "knee,lumbar_spine", "format": "superset",
        "exclude": "ex_WOZL6H,ex_KK4RJV", "seed": "abc123", "model": "female", "lang": "de",
    }


def test_workout_generate_passes_strings_through_and_drops_none(mock_http):
    mock = mock_http({"json": _session_response()})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.workout.generate(equipment="home", avoidJoints="shoulder,wrist", exclude="ex_SAWOOH", seed=None)
    assert mock.last.query == {"equipment": "home", "avoidJoints": "shoulder,wrist", "exclude": "ex_SAWOOH"}

    wx.v2.workout.generate(format="circuit")
    assert mock.last.query == {"format": "circuit"}

    wx.v2.workout.generate()
    assert mock.last.url == "https://api.workoutxapp.com/v2/workout/generate"


def test_workout_program_maps_params(mock_http):
    mock = mock_http({"json": _program_response()})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.workout.program(goal="general_fitness", level="beginner", weeks=16, daysPerWeek=5, duration=50,
                          equipment=["barbell", "dumbbell"], avoidJoints=("shoulder", "elbow"), format="straight",
                          seed="plan-7", model="male", lang="fr")

    assert mock.last.path == "/v2/workout/program"
    assert mock.last.query == {
        "goal": "general_fitness", "level": "beginner", "weeks": "16", "daysPerWeek": "5", "duration": "50",
        "equipment": "barbell,dumbbell", "avoidJoints": "shoulder,elbow", "format": "straight",
        "seed": "plan-7", "model": "male", "lang": "fr",
    }

    wx.v2.workout.program(avoidJoints="knee")
    assert mock.last.query == {"avoidJoints": "knee"}


def test_workout_generate_returns_session_shape(mock_http):
    mock_http({"json": _session_response()})
    wx = WorkoutX(api_key="wx_test")

    session = wx.v2.workout.generate(goal="muscle_gain", avoidJoints=["knee"])

    assert (session["seed"], session["split"], session["format"]) == ("doc1", "full_body", "superset")
    assert session["avoidJoints"] == ["knee"]
    assert "circuit" not in session
    assert session["summary"]["workingSets"] == 9
    assert "Dumbbell Front Squat" in session["warmup"]["rampUp"]
    assert [s["exercise"]["id"] for s in session["warmup"]["items"]] == ["ex_L4EMF6", "ex_UBH37I"]
    squat, hinge, press = session["exercises"]
    assert (squat["block"], squat["role"], squat["pattern"], squat["rir"], squat["load"]) == ("A", "main", "squat", 2, "70–80% of 1RM")
    assert squat["alternatives"][0] == {"id": "ex_O6QQUL", "name": "Bodyweight Full Squat With Overhead Press",
                                        "equipment": "Body Weight", "model": "male"}
    assert [hinge["block"], press["block"]] == ["B1", "B2"]  # a superset
    assert press["cue"] is None
    assert session["cooldown"]["items"][0]["perSide"] is True


def test_fresh_media_reuses_session_warmup_main_and_cooldown_links(mock_http):
    mock = mock_http(lambda req: {"json": _session_response()} if req.path == "/v2/workout/generate"
                     else {"json": {"id": req.path.split("/")[3], "media": _media("fetched")}})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.workout.generate(seed="doc1")

    assert "s=warm" in wx.v2.fresh_media("ex_L4EMF6")["mp4"]     # warm-up
    assert "s=warm2" in wx.v2.fresh_media("ex_UBH37I")["mp4"]    # warm-up
    assert "s=main" in wx.v2.fresh_media("ex_TFXRNX")["mp4"]     # main lift
    assert "s=b1" in wx.v2.fresh_media("ex_UA3FUQ")["mp4"]       # superset
    assert "s=cool" in wx.v2.fresh_media("ex_CWLQWA")["mp4"]     # cool-down
    assert len(mock.calls) == 1

    # Alternatives are light (no media): their links are fetched.
    assert "s=fetched" in wx.v2.fresh_media("ex_O6QQUL")["mp4"]
    assert mock.last.path == "/v2/exercises/ex_O6QQUL/media"
    assert len(mock.calls) == 2


def test_workout_circuit_session(mock_http):
    circuit = dict(_session_response(), goal="fat_loss", split="conditioning", format="circuit",
                   circuit={"rounds": 3, "workSeconds": 40, "restSeconds": 20, "restBetweenRoundsSeconds": 75},
                   exercises=[{"order": 1, "block": "A", "role": "conditioning", "pattern": "cardio", "sets": 1, "rounds": 3,
                               "durationSeconds": 40, "perSide": False, "restSeconds": 20, "cue": None,
                               "rationale": "Conditioning: cardio to keep your heart rate up.", "alternatives": [],
                               "exercise": _exercise("ex_JJACK1", "jack", "Jumping Jack")}])
    mock = mock_http({"json": circuit})
    wx = WorkoutX(api_key="wx_test")

    session = wx.v2.workout.generate(goal="fat_loss", format="circuit")

    assert session["circuit"] == {"rounds": 3, "workSeconds": 40, "restSeconds": 20, "restBetweenRoundsSeconds": 75}
    assert (session["exercises"][0]["rounds"], session["exercises"][0]["durationSeconds"]) == (3, 40)
    assert "s=jack" in wx.v2.fresh_media("ex_JJACK1")["mp4"]
    assert len(mock.calls) == 1


def test_workout_program_returns_program_shape(mock_http):
    mock_http({"json": _program_response()})
    wx = WorkoutX(api_key="wx_test")

    program = wx.v2.workout.program(weeks=6, seed="doc2")

    assert (program["seed"], program["weeks"], program["daysPerWeek"]) == ("doc2", 6, 3)
    assert [(d["weekday"], d["session"]) for d in program["schedule"]] == [("Monday", "A"), ("Wednesday", "B"), ("Friday", "C")]
    assert program["progressionModel"]["deloadEvery"] == 5
    assert program["blocks"][0] == {"block": 1, "weeks": [1, 2, 3, 4, 5], "focus": "Foundation", "deloadWeek": 5}
    assert program["weeklyVolume"][1]["status"] == "low"
    session_a = program["sessions"][0]
    assert session_a["warmup"]["items"][0]["exerciseId"] == "ex_YOPLC7"
    assert session_a["exercises"][0]["pattern"] == "squat"

    deload = program["program"][1]
    assert (deload["week"], deload["phase"], deload["deload"]) == (5, "deload", True)
    squat = deload["days"][0]["exercises"][0]
    assert (squat["exerciseId"], squat["sets"], squat["rir"]) == ("ex_NEMYLA", 2, 4)
    assert "exercise" not in squat  # light refs: the full exercise is in exerciseLibrary
    library = {e["id"] for e in program["exerciseLibrary"]}
    assert all(x["exerciseId"] in library for w in program["program"] for d in w["days"] for x in d["exercises"])


def test_fresh_media_reuses_program_exercise_library_links(mock_http):
    mock = mock_http(lambda req: {"json": _program_response()} if req.path == "/v2/workout/program"
                     else {"json": {"id": req.path.split("/")[3], "media": _media("fetched")}})
    wx = WorkoutX(api_key="wx_test")

    wx.v2.workout.program(weeks=6)

    assert "s=lib-squat" in wx.v2.fresh_media("ex_NEMYLA")["mp4"]     # main lift
    assert "s=lib-bench" in wx.v2.fresh_media("ex_SAWOOH")["mp4"]
    assert "s=lib-walk" in wx.v2.fresh_media("ex_YOPLC7")["mp4"]      # warm-up
    assert "s=lib-stretch" in wx.v2.fresh_media("ex_5P2L5F")["mp4"]   # cool-down
    assert len(mock.calls) == 1

    # Not in the library (a swap suggestion): fetched.
    wx.v2.fresh_media("ex_NN32EP")
    assert mock.last.path == "/v2/exercises/ex_NN32EP/media"


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
