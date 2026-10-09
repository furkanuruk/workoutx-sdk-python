from datetime import datetime, timedelta, timezone

from workoutx import WorkoutX


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
