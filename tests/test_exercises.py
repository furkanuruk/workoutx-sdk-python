import pytest

from workoutx import WorkoutX, WorkoutXError


def test_list_sends_api_key_and_pagination(mock_http):
    mock = mock_http({"json": {"total": 1, "count": 1, "data": [{"id": "0001"}]}})
    wx = WorkoutX(api_key="wx_test")

    page = wx.exercises.list(limit=20, offset=40)

    assert page["data"][0]["id"] == "0001"
    req = mock.last
    assert req.path == "/v1/exercises"
    assert req.query == {"limit": "20", "offset": "40"}
    assert req.headers["x-workoutx-key"] == "wx_test"
    assert "authorization" not in req.headers


def test_get_encodes_id(mock_http):
    mock = mock_http({"json": {"id": "0001"}})
    wx = WorkoutX(api_key="wx_test")
    wx.exercises.get("00 1")
    assert mock.last.path == "/v1/exercises/00%201"


def test_by_name_route(mock_http):
    mock = mock_http({"json": [{"id": "0007", "name": "lunges"}]})
    wx = WorkoutX(api_key="wx_test")
    res = wx.exercises.by_name("lunges", limit=1)
    assert res[0]["name"] == "lunges"
    assert mock.last.path == "/v1/exercises/name/lunges"
    assert mock.last.query == {"limit": "1"}


def test_find_falls_back_to_name_on_404(mock_http):
    def reply(req):
        if req.path == "/v1/exercises/lunges":
            return {"status": 404, "json": {"error": "Not Found"}}
        return {"json": [{"id": "0007", "name": "lunges"}]}

    mock = mock_http(reply)
    wx = WorkoutX(api_key="wx_test")
    ex = wx.exercises.find("lunges")
    assert ex["id"] == "0007"
    assert len(mock.calls) == 2


def test_find_returns_none_when_no_match(mock_http):
    def reply(req):
        if req.path.startswith("/v1/exercises/name/"):
            return {"json": []}
        return {"status": 404, "json": {"error": "Not Found"}}

    mock_http(reply)
    wx = WorkoutX(api_key="wx_test")
    assert wx.exercises.find("nope") is None


def test_structured_error(mock_http):
    mock_http({"status": 404, "json": {"error": "Not Found", "message": "no such", "tip": "use by_name"}})
    wx = WorkoutX(api_key="wx_test")
    with pytest.raises(WorkoutXError) as ei:
        wx.exercises.get("bad")
    err = ei.value
    assert err.status == 404
    assert err.code == "Not Found"
    assert str(err) == "no such"
    assert err.tip == "use by_name"
    assert err.is_not_found


def test_workout_generate_query(mock_http):
    mock = mock_http({"json": {"days": []}})
    wx = WorkoutX(api_key="wx_test")
    wx.workout.generate(goal="hypertrophy", days=4)
    assert mock.last.path == "/v1/workout/generate"
    assert mock.last.query == {"goal": "hypertrophy", "days": "4"}


def test_gif_get_appends_extension_and_requests_raw(mock_http):
    mock = mock_http({"body": "GIF89a"})
    wx = WorkoutX(api_key="wx_test")
    data = wx.gifs.get("0001")
    assert data == b"GIF89a"
    assert mock.last.path == "/v1/gifs/0001.gif"
    assert mock.last.headers["accept"] == "*/*"


def test_gif_url_no_request():
    wx = WorkoutX(api_key="wx_test")
    assert wx.gif_url("0001") == "https://api.workoutxapp.com/v1/gifs/0001.gif?api-key=wx_test"
