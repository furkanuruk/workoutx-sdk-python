"""Subscription billing (/v1/billing/*). Requires Bearer auth.

``POST /v1/billing/webhook`` (Stripe's server-to-server callback) is
intentionally not wrapped — it requires the raw request body and
Stripe-Signature header from an actual HTTP server, not a client SDK call.
"""
from __future__ import annotations

from typing import Any, Dict

from .._http import HttpClient


class BillingResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def status(self) -> Dict[str, Any]:
        """Current subscription status, plan, and renewal date."""
        return self._http.request("/v1/billing/status", auth="bearer")

    def checkout(self, plan_id: str, billing_cycle: str = "monthly") -> Dict[str, Any]:
        """Create a Stripe Checkout session. ``plan_id`` is basic/pro/ultra.

        Returns ``{"url": ...}`` — redirect the user there to complete payment.
        """
        return self._http.request(
            "/v1/billing/checkout",
            auth="bearer",
            method="POST",
            body={"planId": plan_id, "billingCycle": billing_cycle},
        )

    def portal(self) -> Dict[str, Any]:
        """Open the Stripe Customer Portal (manage/cancel subscription)."""
        return self._http.request("/v1/billing/portal", auth="bearer", method="POST")
