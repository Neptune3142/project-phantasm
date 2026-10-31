"""Google Gemini threat intelligence service.

Uses the official Gemini REST API via httpx. Falls back to the deterministic
rules engine when no API key is configured, on connection failure, or when
the structured response fails validation.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import httpx

from app.config import get_settings, mask_secret
from app.schemas import GeminiAssessment, UserTelemetryIn
from app.services import rules_engine

logger = logging.getLogger("phantasm.gemini")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 2
RETRY_BACKOFF = 1.0

# Schema enforced on Gemini structured responses. Aligned with GeminiAssessment.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "threat_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "risk_category": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        },
        "reasoning": {"type": "string"},
        "risk_factors": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommended_action": {
            "type": "string",
            "enum": ["MONITOR", "FLAG", "REQUIRE_REVOCATION_APPROVAL", "REVOKE_IMMEDIATELY"],
        },
        "epitaph_summary": {"type": "string"},
    },
    "required": [
        "threat_score",
        "risk_category",
        "reasoning",
        "risk_factors",
        "recommended_action",
        "epitaph_summary",
    ],
}

SYSTEM_PROMPT = (
    "You are PROJECT PHANTASM, an automated cybersecurity threat intelligence "
    "engine specialising in zombie credentials — abandoned, inactive, or "
    "compromised accounts that retain access to sensitive systems. "
    "Analyse the supplied security telemetry and produce a structured JSON "
    "assessment. Be technically rigorous, cite the indicators in the input, "
    "and use the LOW (0-24), MEDIUM (25-49), HIGH (50-74), CRITICAL (75-100) "
    "scale. The epitaph_summary must be a single darkly witty Halloween-themed "
    "sentence that is professionally appropriate for a security incident report."
)


def _build_user_prompt(t: UserTelemetryIn) -> str:
    return (
        "Assess the following security telemetry for a single user account. "
        "Return ONLY the JSON object defined by the schema — no commentary, "
        "no markdown fences.\n\n"
        f"Email: {t.email}\n"
        f"Role: {t.role}\n"
        f"Account type: {t.account_type}\n"
        f"Privilege level: {t.privilege_level}\n"
        f"Days since last activity: {t.last_active_days}\n"
        f"Failed login attempts: {t.failed_login_attempts}\n"
        f"Location anomaly detected: {t.location_anomaly}\n"
        f"Accessed resources: {', '.join(t.accessed_resources) or 'none'}\n\n"
        "Score 0-100 with justification and a recommended action."
    )


class GeminiService:
    """Wraps Gemini REST calls + validation + fallback."""

    def __init__(self, settings=None) -> None:
        self.settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def assess(self, telemetry: UserTelemetryIn) -> GeminiAssessment:
        """Return a structured assessment — Gemini if configured, rules engine otherwise."""
        if not self.settings.has_gemini():
            logger.info("Gemini key not configured — using rules engine.")
            return rules_engine.assess(telemetry)

        try:
            raw = await self._call_gemini(telemetry)
            assessment = self._validate(raw)
            if assessment is None:
                logger.warning("Gemini response failed validation — falling back to rules engine.")
                return rules_engine.assess(telemetry)
            return assessment
        except Exception as exc:
            logger.error("Gemini call failed: %s — falling back to rules engine.", exc)
            return rules_engine.assess(telemetry)

    async def test_connection(self) -> dict:
        """Send a tiny test prompt to verify the API key and model."""
        if not self.settings.has_gemini():
            return {
                "connected": False,
                "detail": "No GEMINI_API_KEY configured.",
                "suggestion": "Create a key at https://aistudio.google.com/app/apikey "
                              "and add it in Settings → Integrations.",
            }
        model = self.settings.gemini_model or "gemini-2.5-flash"
        url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={self.settings.gemini_api_key}"
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": "Respond with the single word: PONG"}],
                }
            ],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 16},
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, json=body)
            if resp.status_code == 200:
                return {
                    "connected": True,
                    "detail": f"Gemini API reachable. Model: {model}. Key: {mask_secret(self.settings.gemini_api_key)}.",
                }
            return {
                "connected": False,
                "detail": f"HTTP {resp.status_code}: {resp.text[:200]}",
                "suggestion": "Check that the API key is valid and the model name is supported "
                              "for your project (see https://ai.google.dev/gemini-api/docs/models).",
            }
        except httpx.HTTPError as exc:
            return {
                "connected": False,
                "detail": f"Network error: {exc}",
                "suggestion": "Verify outbound connectivity to generativelanguage.googleapis.com.",
            }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    async def _call_gemini(self, telemetry: UserTelemetryIn) -> dict:
        """Call the Gemini REST endpoint with retry + structured output."""
        model = self.settings.gemini_model or "gemini-2.5-flash"
        url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={self.settings.gemini_api_key}"
        body = {
            "contents": [
                {"role": "user", "parts": [{"text": _build_user_prompt(telemetry)}]}
            ],
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json",
                "responseSchema": RESPONSE_SCHEMA,
            },
        }
        last_exc: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.post(url, json=body)
                if resp.status_code == 200:
                    return self._extract_text(resp.json())
                if resp.status_code in {429, 500, 502, 503, 504} and attempt <= MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF * attempt)
                    continue
                # Non-retryable error — surface to caller
                raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:300]}")
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt <= MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF * attempt)
                    continue
                raise
        if last_exc:
            raise last_exc
        raise RuntimeError("Gemini call failed without exception.")

    @staticmethod
    def _extract_text(payload: dict) -> dict:
        """Extract the candidate text and parse it as JSON."""
        candidates = payload.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise RuntimeError("Gemini returned no content parts.")
        text = parts[0].get("text", "")
        if not text:
            raise RuntimeError("Gemini returned empty text.")
        return json.loads(text)

    @staticmethod
    def _validate(raw: dict) -> Optional[GeminiAssessment]:
        """Validate the parsed JSON against GeminiAssessment."""
        try:
            return GeminiAssessment.model_validate(raw)
        except Exception as exc:
            logger.warning("Gemini validation failed: %s | raw=%s", exc, raw)
            return None


# Module-level singleton for simple dependency injection.
gemini_service = GeminiService()
