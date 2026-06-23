from workoutx import WorkoutX


def test_status_uses_bearer(mock_http):
    mock = mock_http({"json": {"status": "active", "plan": "pro"}})
    wx = WorkoutX(scan_token="jwt")
    s = wx.billing.status()
    assert s["plan"] == "pro"
    assert mock.last.path == "/v1/billing/status"
    assert mock.last.headers["authorization"] == "Bearer jwt"


def test_checkout_posts_plan_and_cycle(mock_http):
    mock = mock_http({"json": {"url": "https://checkout.stripe.com/abc"}})
    wx = WorkoutX(scan_token="jwt")
    out = wx.billing.checkout("pro", "yearly")
    assert out["url"] == "https://checkout.stripe.com/abc"
    assert mock.last.method == "POST"
    assert mock.last.path == "/v1/billing/checkout"
    assert mock.last.body == {"planId": "pro", "billingCycle": "yearly"}


def test_checkout_defaults_monthly(mock_http):
    mock = mock_http({"json": {"url": "x"}})
    wx = WorkoutX(scan_token="jwt")
    wx.billing.checkout("basic")
    assert mock.last.body == {"planId": "basic", "billingCycle": "monthly"}


def test_portal_posts_no_body(mock_http):
    mock = mock_http({"json": {"url": "https://billing.stripe.com/p"}})
    wx = WorkoutX(scan_token="jwt")
    wx.billing.portal()
    assert mock.last.method == "POST"
    assert mock.last.path == "/v1/billing/portal"
    assert mock.last.body is None
