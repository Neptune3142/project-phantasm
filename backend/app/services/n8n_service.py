"""n8n webhook communication service.

Sends the exorcism payload to the configured n8n webhook and waits for the
workflow execution response. Falls back to a local pipeline runner when n8n
is not configured (the Python pipeline runs the *same* steps as n8n would, so
the simulation is faithful, not cosmetic).
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import get_settings, mask_secret

logger = logging.getLogger("phantasm.n8n")


class N8nService:
    """Wraps webhook communication with the n8n automation engine."""

    def __init__(self, settings=None) -> None:
        self.settings = settings or get_settings()

    async def submit_exorcism(self, payload: dict) -> dict:
        """POST to the n8n webhook and return the response.

        Returns a dict with keys: `submitted`, `workflow_status`, `detail`.
        On failure, returns `submitted=False` with a helpful `detail` — never raises.
        """
        if not self.settings.has_n8n():
            return {
                "submitted": False,
                "workflow_status": "skipped",
                "detail": "No N8N_WEBHOOK_URL configured — local pipeline ran instead.",
            }
        headers = {}
        if self.settings.n8n_api_key:
            headers["X-N8N-API-KEY"] = self.settings.n8n_api_key
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self.settings.n8n_webhook_url, json=payload, headers=headers)
            if resp.status_code in (200, 201, 202):
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw": resp.text[:500]}
                return {
                    "submitted": True,
                    "workflow_status": "executed",
                    "detail": "n8n accepted the webhook payload.",
                    "response": body,
                }
            return {
                "submitted": False,
                "workflow_status": "error",
                "detail": f"n8n returned HTTP {resp.status_code}: {resp.text[:300]}",
            }
        except httpx.HTTPError as exc:
            return {
                "submitted": False,
                "workflow_status": "unreachable",
                "detail": f"Network error contacting n8n: {exc}",
            }

    async def test_connection(self) -> dict:
        """Send a harmless ping to the n8n webhook to verify reachability."""
        if not self.settings.has_n8n():
            return {
                "connected": False,
                "detail": "No N8N_WEBHOOK_URL configured.",
                "suggestion": "Run `docker compose up n8n` (see n8n/README.md), "
                              "import phantasm_workflow.json, activate it, then copy "
                              "the webhook URL into Settings → Integrations.",
            }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.settings.n8n_webhook_url,
                    json={"ping": "phantasm", "type": "connection_test"},
                )
            if resp.status_code in (200, 201, 202):
                return {
                    "connected": True,
                    "detail": f"n8n webhook reachable at {mask_secret(self.settings.n8n_webhook_url)} "
                              f"(HTTP {resp.status_code}).",
                }
            return {
                "connected": False,
                "detail": f"n8n returned HTTP {resp.status_code}. The instance is reachable "
                          f"but the workflow may not be active.",
                "suggestion": "Open n8n → activate the imported Phantasm workflow → "
                              "verify the webhook path matches N8N_WEBHOOK_URL.",
            }
        except httpx.HTTPError as exc:
            return {
                "connected": False,
                "detail": f"Cannot reach n8n: {exc}",
                "suggestion": "Confirm n8n is running (`docker compose ps`) and that "
                              "N8N_WEBHOOK_URL is correct.",
            }


n8n_service = N8nService()
