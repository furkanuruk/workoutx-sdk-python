import pytest

from workoutx import WorkoutX, WorkoutXConnectionError
import workoutx._http as _http_mod


def test_scan_auto_login_then_cache(mock_http):
    def reply(req):
        if req.path == "/v1/auth/login":
            return {"json": {"token": "tok-1", "user": {}, "apiKeys": []}}
        return {"json": {"credits": 5}}

    mock = mock_http(reply)
    wx = WorkoutX(scan_email="a@b.com", scan_password="pw")

    credits = wx.scan.credits()
    assert credits["credits"] == 5
    assert mock.calls[0].path == "/v1/auth/login"
    assert mock.last.headers["authorization"] == "Bearer tok-1"

    wx.scan.me()
    assert len([c for c in mock.calls if c.path == "/v1/auth/login"]) == 1


def test_scan_packs_is_public(mock_http):
    mock = mock_http({"json": {"packs": []}})
    wx = WorkoutX()
    wx.scan.packs()
    assert mock.last.path == "/v1/scan/packs"
    assert "authorization" not in mock.last.headers
    assert "x-workoutx-key" not in mock.last.headers


def test_retry_on_503_then_success(mock_http, monkeypatch):
    monkeypatch.setattr(_http_mod.time, "sleep", lambda *_: None)
    state = {"n": 0}

    def reply(req):
        state["n"] += 1
        if state["n"] < 2:
            return {"status": 503, "json": {"error": "Service Unavailable"}}
        return {"json": {"ok": True}}

    mock_http(reply)
    wx = WorkoutX(api_key="wx_test", max_retries=2)
    assert wx.exercises.list() == {"ok": True}
    assert state["n"] == 2


def test_connection_error_after_retries(monkeypatch):
    monkeypatch.setattr(_http_mod.time, "sleep", lambda *_: None)

    def boom(*a, **k):
        raise OSError("network down")

    monkeypatch.setattr(_http_mod.urllib.request, "urlopen", boom)
    wx = WorkoutX(api_key="wx_test", max_retries=1)
    with pytest.raises(WorkoutXConnectionError):
        wx.exercises.list()


def test_custom_headers_merged(mock_http):
    mock = mock_http({"json": {"data": []}})
    wx = WorkoutX(api_key="wx_test", headers={"X-Trace": "abc"})
    wx.exercises.list()
    assert mock.last.headers["x-trace"] == "abc"
    assert "workoutx-sdk-python" in mock.last.headers["user-agent"]
