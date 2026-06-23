"""Account, API-key, and webhook management (/v1/auth/*).

``register``, ``login``, ``forgot_password``, ``reset_password``,
``verify_email``, and ``resend_verification`` are public — no token needed.
Everything else requires the Bearer token returned by ``login``.

Google OAuth (/v1/auth/google) is a browser-redirect flow and is not wrapped
here — it only makes sense from a web app, not an SDK call.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

from .._http import HttpClient


class AuthResource:
    def __init__(
        self,
        http: HttpClient,
        on_login: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._http = http
        self._on_login = on_login

    def register(self, *, email: str, password: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new account. Sends a verification email; no token issued yet."""
        return self._http.request(
            "/v1/auth/register",
            method="POST",
            body={"email": email, "password": password, "name": name},
        )

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Log in and receive a Bearer token (also used by ``scan`` / ``billing``)."""
        res = self._http.request(
            "/v1/auth/login", method="POST", body={"email": email, "password": password}
        )
        token = res.get("token") if isinstance(res, dict) else None
        if token and self._on_login:
            self._on_login(token)
        return res

    def me(self) -> Dict[str, Any]:
        """Get the current user's profile."""
        return self._http.request("/v1/auth/me", auth="bearer")

    def update_me(self, name: str) -> Dict[str, Any]:
        """Update the current user's display name."""
        return self._http.request("/v1/auth/me", auth="bearer", method="PATCH", body={"name": name})

    def change_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """Change the current user's password."""
        return self._http.request(
            "/v1/auth/change-password",
            auth="bearer",
            method="POST",
            body={"currentPassword": current_password, "newPassword": new_password},
        )

    def list_keys(self) -> List[Dict[str, Any]]:
        """List the current user's API keys."""
        return self._http.request("/v1/auth/keys", auth="bearer")

    def create_key(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new API key."""
        return self._http.request("/v1/auth/keys", auth="bearer", method="POST", body={"name": name})

    def delete_key(self, key_id: str) -> Dict[str, Any]:
        """Delete an API key by ID."""
        return self._http.request(f"/v1/auth/keys/{quote(key_id)}", auth="bearer", method="DELETE")

    def update_key_plan(self, key_id: str, plan_id: str) -> Dict[str, Any]:
        """Change the plan assigned to an API key."""
        return self._http.request(
            f"/v1/auth/keys/{quote(key_id)}/plan",
            auth="bearer",
            method="PATCH",
            body={"planId": plan_id},
        )

    def usage(self, *, days: Optional[int] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Usage statistics for the current user (optionally for one API key)."""
        return self._http.request(
            "/v1/auth/usage", auth="bearer", query={"days": days, "apiKey": api_key}
        )

    def forgot_password(self, email: str) -> Dict[str, Any]:
        """Request a password-reset email. Always succeeds (no email enumeration)."""
        return self._http.request("/v1/auth/forgot-password", method="POST", body={"email": email})

    def reset_password(self, token: str, password: str) -> Dict[str, Any]:
        """Complete a password reset using the token from ``forgot_password``."""
        return self._http.request(
            "/v1/auth/reset-password", method="POST", body={"token": token, "password": password}
        )

    def verify_email(self, token: str) -> Dict[str, Any]:
        """Verify an email address using the token from the verification email."""
        return self._http.request("/v1/auth/verify-email", query={"token": token})

    def resend_verification(self, email: str) -> Dict[str, Any]:
        """Resend the verification email. Always succeeds (no email enumeration)."""
        return self._http.request("/v1/auth/resend-verification", method="POST", body={"email": email})

    def get_webhook(self) -> Dict[str, Any]:
        """Get the current user's registered webhook URL."""
        return self._http.request("/v1/auth/webhook", auth="bearer")

    def set_webhook(self, webhook_url: Optional[str]) -> Dict[str, Any]:
        """Set (or clear, with ``None``) the webhook URL."""
        return self._http.request(
            "/v1/auth/webhook", auth="bearer", method="PATCH", body={"webhookUrl": webhook_url}
        )

    def test_webhook(self) -> Dict[str, Any]:
        """Send a test event to the registered webhook URL."""
        return self._http.request("/v1/auth/webhook/test", auth="bearer", method="POST")
