import pytest

from workoutx import WorkoutX, WorkoutXError


def test_register_posts_body(mock_http):
    mock = mock_http({"status": 201, "json": {"requiresVerification": True}})
    wx = WorkoutX()
    wx.auth.register(email="a@b.com", password="supersecret", name="A")
    req = mock.last
    assert req.method == "POST"
    assert req.path == "/v1/auth/register"
    assert req.body == {"email": "a@b.com", "password": "supersecret", "name": "A"}


def test_login_caches_token_for_bearer_calls(mock_http):
    def reply(req):
        if req.path == "/v1/auth/login":
            return {"json": {"token": "jwt-123", "user": {"id": "u1"}, "apiKeys": []}}
        return {"json": {"id": "u1"}}

    mock = mock_http(reply)
    wx = WorkoutX()

    res = wx.auth.login("a@b.com", "pw")
    assert res["token"] == "jwt-123"

    wx.auth.me()
    assert mock.last.path == "/v1/auth/me"
    assert mock.last.headers["authorization"] == "Bearer jwt-123"
    assert len([c for c in mock.calls if c.path == "/v1/auth/login"]) == 1


def test_update_me_uses_patch(mock_http):
    mock = mock_http({"json": {"id": "u1", "name": "New"}})
    wx = WorkoutX(scan_token="t")
    wx.auth.update_me("New")
    assert mock.last.method == "PATCH"
    assert mock.last.path == "/v1/auth/me"
    assert mock.last.body == {"name": "New"}


def test_key_crud_verbs(mock_http):
    mock = mock_http({"json": {}})
    wx = WorkoutX(scan_token="t")

    wx.auth.create_key("CI key")
    assert mock.last.method == "POST" and mock.last.path == "/v1/auth/keys"

    wx.auth.delete_key("key_42")
    assert mock.last.method == "DELETE" and mock.last.path == "/v1/auth/keys/key_42"

    wx.auth.update_key_plan("key_42", "pro")
    assert mock.last.method == "PATCH"
    assert mock.last.path == "/v1/auth/keys/key_42/plan"
    assert mock.last.body == {"planId": "pro"}


def test_verify_email_query_param_public(mock_http):
    mock = mock_http({"json": {"verified": True}})
    wx = WorkoutX()
    wx.auth.verify_email("tok-abc")
    assert mock.last.path == "/v1/auth/verify-email"
    assert mock.last.query == {"token": "tok-abc"}
    assert "authorization" not in mock.last.headers


def test_set_webhook_null_clears(mock_http):
    mock = mock_http({"json": {"webhookUrl": None}})
    wx = WorkoutX(scan_token="t")
    wx.auth.set_webhook(None)
    assert mock.last.method == "PATCH"
    assert mock.last.path == "/v1/auth/webhook"
    assert mock.last.body == {"webhookUrl": None}


def test_bearer_without_credentials_raises_before_request(mock_http):
    mock = mock_http({"json": {}})
    wx = WorkoutX(api_key="wx_test")
    with pytest.raises(WorkoutXError) as ei:
        wx.auth.me()
    assert ei.value.status == 401
    assert len(mock.calls) == 0
