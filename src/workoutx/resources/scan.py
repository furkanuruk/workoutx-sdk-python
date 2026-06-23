"""Access to the Body Scan product (/v1/scan/*). Requires Bearer auth."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from .._http import HttpClient


class ScanResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def credits(self) -> Dict[str, Any]:
        return self._http.request("/v1/scan/credits", auth="bearer")

    def me(self) -> Dict[str, Any]:
        return self._http.request("/v1/scan/me", auth="bearer")

    def history(self, *, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        return self._http.request("/v1/scan/history", auth="bearer", query={"limit": limit, "offset": offset})

    def list_keys(self) -> List[Dict[str, Any]]:
        return self._http.request("/v1/scan/keys", auth="bearer")

    def create_key(self, name: str) -> Dict[str, Any]:
        return self._http.request("/v1/scan/keys", auth="bearer", method="POST", body={"name": name})

    def delete_key(self, key_id: str) -> Dict[str, Any]:
        return self._http.request(f"/v1/scan/keys/{quote(key_id)}", auth="bearer", method="DELETE")

    def checkout(self, **body: Any) -> Dict[str, Any]:
        return self._http.request("/v1/scan/checkout", auth="bearer", method="POST", body=body)

    def packs(self) -> Dict[str, Any]:
        """Public list of credit packs (no auth required)."""
        return self._http.request("/v1/scan/packs")
