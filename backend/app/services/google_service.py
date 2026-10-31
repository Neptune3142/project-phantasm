"""Google Sheets + Gmail integration service.

When credentials are configured, performs genuine API calls. Otherwise
returns a clearly-labelled "simulation" status. The Python backend always
persists the audit row locally first, so the Google integrations are a
secondary mirror, never the source of truth.
"""
from __future__ import annotations

import base64
import json
import logging
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.config import get_settings
from app.services.audit_service import SHEET_HEADERS, to_sheet_row
from app.models import SecurityIncident

logger = logging.getLogger("phantasm.google")


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


async def _get_access_token(settings) -> Optional[str]:
    """Exchange the refresh token for a fresh access token."""
    if not (settings.google_client_id and settings.google_client_secret and settings.google_refresh_token):
        return None
    data = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "refresh_token": settings.google_refresh_token,
        "grant_type": "refresh_token",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=data)
        if resp.status_code != 200:
            logger.warning("Google OAuth token refresh failed: %s", resp.text[:200])
            return None
        return resp.json().get("access_token")
    except httpx.HTTPError as exc:
        logger.warning("Google OAuth HTTP error: %s", exc)
        return None


class GoogleService:
    """Sheets + Gmail via REST OAuth."""

    def __init__(self, settings=None) -> None:
        self.settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Sheets
    # ------------------------------------------------------------------
    async def append_incident_row(self, incident: SecurityIncident) -> dict:
        if not self.settings.has_google_sheets():
            return {"written": False, "detail": "Google Sheets not configured — skipped."}
        token = await _get_access_token(self.settings)
        if token is None:
            return {"written": False, "detail": "Could not obtain Google access token."}
        row = await to_sheet_row(incident)
        # Ensure headers exist on first write.
        await self._ensure_headers(token)
        body = {"values": [row]}
        url = (
            f"{SHEETS_API}/{self.settings.google_sheet_id}/values/"
            f"A1:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
        )
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=body, headers=headers)
            if resp.status_code in (200, 201):
                return {"written": True, "detail": "Audit row appended to Google Sheet."}
            return {"written": False, "detail": f"Sheets API HTTP {resp.status_code}: {resp.text[:200]}"}
        except httpx.HTTPError as exc:
            return {"written": False, "detail": f"Sheets API network error: {exc}"}

    async def _ensure_headers(self, token: str) -> None:
        url = f"{SHEETS_API}/{self.settings.google_sheet_id}/values/A1:Z1"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                values = data.get("values", [])
                if not values or not values[0]:
                    body = {"values": [SHEET_HEADERS]}
                    await client.put(url, json=body, headers=headers)
        except httpx.HTTPError:
            pass

    async def test_sheets(self) -> dict:
        if not self.settings.has_google_sheets():
            return {
                "connected": False,
                "detail": "Google Sheets credentials incomplete.",
                "suggestion": "Provide GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, "
                              "GOOGLE_REFRESH_TOKEN and GOOGLE_SHEET_ID in Settings.",
            }
        token = await _get_access_token(self.settings)
        if token is None:
            return {"connected": False, "detail": "OAuth token refresh failed."}
        url = f"{SHEETS_API}/{self.settings.google_sheet_id}?fields=spreadsheetId,properties.title"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                title = resp.json().get("properties", {}).get("title", "?")
                return {"connected": True, "detail": f"Connected to spreadsheet '{title}'."}
            return {"connected": False, "detail": f"Sheets API HTTP {resp.status_code}: {resp.text[:200]}"}
        except httpx.HTTPError as exc:
            return {"connected": False, "detail": f"Sheets API network error: {exc}"}

    # ------------------------------------------------------------------
    # Gmail
    # ------------------------------------------------------------------
    async def send_incident_email(self, incident: SecurityIncident) -> dict:
        if not self.settings.has_gmail():
            return {"sent": False, "detail": "Gmail credentials not configured — skipped."}
        token = await _get_access_token(self.settings)
        if token is None:
            return {"sent": False, "detail": "Could not obtain Google access token."}
        subject = f"[PHANTASM] {incident.risk_category} incident — {incident.user.email if incident.user else '?'}"
        body = self._build_email_body(incident)
        message = MIMEText(body, "plain", "utf-8")
        message["to"] = self.settings.gmail_recipient
        message["from"] = self.settings.gmail_sender
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(GMAIL_API, json={"raw": raw}, headers=headers)
            if resp.status_code in (200, 201):
                msg_id = resp.json().get("id", "?")
                return {"sent": True, "detail": f"Incident email sent (gmail id={msg_id})."}
            return {"sent": False, "detail": f"Gmail API HTTP {resp.status_code}: {resp.text[:200]}"}
        except httpx.HTTPError as exc:
            return {"sent": False, "detail": f"Gmail API network error: {exc}"}

    async def test_gmail(self) -> dict:
        if not self.settings.has_gmail():
            return {
                "connected": False,
                "detail": "Gmail credentials incomplete.",
                "suggestion": "Set GMAIL_SENDER and GMAIL_RECIPIENT, plus the Google "
                              "OAuth credentials (the same refresh token works for both "
                              "Sheets and Gmail if both APIs are enabled).",
            }
        token = await _get_access_token(self.settings)
        if token is None:
            return {"connected": False, "detail": "OAuth token refresh failed."}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://gmail.googleapis.com/gmail/v1/users/me/profile",
                    headers={"Authorization": f"Bearer {token}"},
                )
            if resp.status_code == 200:
                addr = resp.json().get("emailAddress", "?")
                return {"connected": True, "detail": f"Gmail connected as {addr}."}
            return {"connected": False, "detail": f"Gmail API HTTP {resp.status_code}: {resp.text[:200]}"}
        except httpx.HTTPError as exc:
            return {"connected": False, "detail": f"Gmail API network error: {exc}"}

    @staticmethod
    def _build_email_body(incident: SecurityIncident) -> str:
        return (
            "PROJECT PHANTASM — Automated Zombie Credential Exorcist\n"
            "=========================================================\n\n"
            f"Incident ID: {incident.incident_id}\n"
            f"User: {incident.user.email if incident.user else 'unknown'}\n"
            f"Timestamp: {incident.timestamp.isoformat() if incident.timestamp else 'N/A'}\n\n"
            f"Threat score: {incident.threat_score}/100\n"
            f"Risk category: {incident.risk_category}\n"
            f"Assessment source: {incident.assessment_source}\n\n"
            f"Reasoning:\n{incident.ai_reasoning or 'N/A'}\n\n"
            f"Risk factors:\n- " + "\n- ".join(incident.risk_factors or ["N/A"]) + "\n\n"
            f"Recommended action: {incident.recommended_action}\n"
            f"Action taken: {incident.action_taken or 'pending'}\n"
            f"Execution status: {incident.execution_status}\n\n"
            f"Epitaph: {incident.epitaph_summary or ''}\n\n"
            "— Project Phantasm automation engine\n"
        )


google_service = GoogleService()
