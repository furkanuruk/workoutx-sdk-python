"""Access to /v1/gifs/* (API-key auth)."""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote, urlencode

from .._http import HttpClient


class GifsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get(self, filename: str) -> bytes:
        """Fetch an exercise GIF as raw bytes. Accepts "0001" or "0001.gif".

        Free plan receives a watermarked variant; paid plans get the original.
        """
        name = filename if filename.lower().endswith(".gif") else f"{filename}.gif"
        return self._http.request(f"/v1/gifs/{quote(name)}", raw=True)

    @staticmethod
    def url(filename: str, *, base_url: str, api_key: Optional[str] = None) -> str:
        """Build a direct GIF URL (no request). Useful for <img src>."""
        name = filename if filename.lower().endswith(".gif") else f"{filename}.gif"
        u = f"{base_url.rstrip('/')}/v1/gifs/{quote(name)}"
        if api_key:
            u += "?" + urlencode({"api-key": api_key})
        return u
