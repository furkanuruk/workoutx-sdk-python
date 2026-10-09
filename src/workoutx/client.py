"""The WorkoutX API client."""
from __future__ import annotations

from typing import Dict, Optional

from ._http import HttpClient
from .resources import (
    ExercisesResource,
    GifsResource,
    WorkoutResource,
    SupplementsResource,
    ScanResource,
    AuthResource,
    BillingResource,
    V2Resource,
)

DEFAULT_BASE_URL = "https://api.workoutxapp.com"
_VERSION = "0.1.0"


class WorkoutX:
    """One client for both products (exercises + body scan).

    Examples
    --------
    >>> wx = WorkoutX(api_key="wx_...", scan_token="eyJ...")
    >>> wx.exercises.by_name("lunges")
    >>> wx.scan.credits()

    For body scan you can pass ``scan_token`` directly, or ``scan_email`` +
    ``scan_password`` to auto-login on first use.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        scan_token: Optional[str] = None,
        scan_email: Optional[str] = None,
        scan_password: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 2,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._scan_email = scan_email
        self._scan_password = scan_password
        self._cached_token = scan_token

        default_headers = {"User-Agent": f"workoutx-sdk-python/{_VERSION}"}
        if headers:
            default_headers.update(headers)

        self._http = HttpClient(
            base_url=self._base_url,
            api_key=api_key,
            get_bearer=self._get_bearer_token,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
        )

        self.exercises = ExercisesResource(self._http)
        self.gifs = GifsResource(self._http)
        self.workout = WorkoutResource(self._http)
        self.supplements = SupplementsResource(self._http)
        self.scan = ScanResource(self._http)
        # A successful auth.login() caches the token so scan/billing work
        # without re-supplying credentials.
        self.auth = AuthResource(self._http, self.set_scan_token)
        self.billing = BillingResource(self._http)
        # API v2: new catalog with signed, expiring media links.
        self.v2 = V2Resource(self._http)

    def gif_url(self, filename: str) -> str:
        """Build a direct GIF URL with the API key in the query string."""
        return GifsResource.url(filename, base_url=self._base_url, api_key=self._api_key)

    def set_scan_token(self, token: str) -> None:
        self._cached_token = token

    # ── internal ──────────────────────────────────────────────────────────────
    def _get_bearer_token(self) -> Optional[str]:
        if self._cached_token:
            return self._cached_token
        if self._scan_email and self._scan_password:
            res = self._http.request(
                "/v1/auth/login",
                method="POST",
                body={"email": self._scan_email, "password": self._scan_password},
            )
            self._cached_token = res.get("token")
            return self._cached_token
        return None
