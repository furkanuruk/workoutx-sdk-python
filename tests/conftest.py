"""Shared test fixtures.

The SDK talks to the network through ``urllib.request.urlopen`` inside
``workoutx._http``. We patch that single function with a recorder that returns
canned responses, so tests run fully offline and assert on the exact request
the SDK built (URL, method, headers, JSON body).
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Union

import pytest

import workoutx._http as _http_mod


class CapturedRequest:
    def __init__(self, req: "urllib.request.Request") -> None:
        self.url: str = req.full_url
        self.method: str = req.get_method()
        # urllib capitalizes header keys; normalise to lowercase for assertions.
        self.headers: Dict[str, str] = {k.lower(): v for k, v in req.headers.items()}
        self.body: Any = json.loads(req.data) if req.data else None

    @property
    def path(self) -> str:
        return urllib.parse.urlsplit(self.url).path

    @property
    def query(self) -> Dict[str, str]:
        return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.url).query))


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False

    def read(self) -> bytes:
        return self._data


Reply = Dict[str, Any]
ReplyFn = Union[Reply, Callable[[CapturedRequest], Reply]]


class MockUrlopen:
    def __init__(self, reply: ReplyFn) -> None:
        self.reply = reply
        self.calls: List[CapturedRequest] = []

    def __call__(self, req: Any, timeout: Any = None, context: Any = None) -> _FakeResponse:
        captured = CapturedRequest(req)
        self.calls.append(captured)
        r = self.reply(captured) if callable(self.reply) else self.reply

        status = r.get("status", 200)
        body = r.get("body")
        if body is None and "json" in r:
            body = json.dumps(r["json"])
        data = (body or "").encode("utf-8") if isinstance(body, str) else (body or b"")

        if status >= 400:
            raise urllib.error.HTTPError(
                captured.url, status, r.get("reason", "Error"),
                r.get("headers", {}), io.BytesIO(data),  # type: ignore[arg-type]
            )
        return _FakeResponse(data)

    @property
    def last(self) -> CapturedRequest:
        return self.calls[-1]


@pytest.fixture
def mock_http(monkeypatch: pytest.MonkeyPatch):
    """Return a factory: ``mock_http(reply)`` patches urlopen and returns the recorder."""
    def _install(reply: ReplyFn) -> MockUrlopen:
        mock = MockUrlopen(reply)
        monkeypatch.setattr(_http_mod.urllib.request, "urlopen", mock)
        return mock

    return _install
