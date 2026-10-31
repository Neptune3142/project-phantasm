"""Integration status + credential configuration + connection tests."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings, mask_secret, reload_settings, set_env
from app.database import get_session
from app.schemas import ConnectionTestResult, CredentialUpdate, GenericMessage, IntegrationStatus
from app.services.gemini_service import gemini_service
from app.services.google_service import google_service
from app.services.n8n_service import n8n_service

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])


def _status_dict(label: str, configured: bool, masked_value: str, hint: str) -> dict:
    return {
        "label": label,
        "configured": configured,
        "status": "connected" if configured else "disconnected",
        "masked_value": masked_value,
        "hint": hint,
    }


@router.get("/status", response_model=IntegrationStatus)
async def integration_status(session: AsyncSession = Depends(get_session)) -> IntegrationStatus:
    s = get_settings()
    return IntegrationStatus(
        gemini=_status_dict(
            "Google Gemini",
            s.has_gemini(),
            mask_secret(s.gemini_api_key),
            f"Model: {s.gemini_model}" if s.gemini_model else "",
        ),
        n8n=_status_dict(
            "n8n Automation",
            s.has_n8n(),
            mask_secret(s.n8n_webhook_url),
            "Webhook endpoint configured" if s.has_n8n() else "No webhook URL",
        ),
        google_sheets=_status_dict(
            "Google Sheets Ledger",
            s.has_google_sheets(),
            mask_secret(s.google_sheet_id),
            "OAuth credentials + sheet ID configured" if s.has_google_sheets() else "Awaiting credentials",
        ),
        gmail=_status_dict(
            "Gmail Notifications",
            s.has_gmail(),
            mask_secret(s.gmail_sender),
            f"Recipient: {s.gmail_recipient}" if s.has_gmail() else "Awaiting sender + recipient",
        ),
        simulation_mode=s.simulation_mode,
        database_url=s.database_url,
    )


@router.post("/credentials", response_model=GenericMessage)
async def update_credential(update: CredentialUpdate) -> GenericMessage:
    set_env(update.key, update.value)
    reload_settings()
    # Re-instantiate service singletons with refreshed settings
    gemini_service.settings = get_settings()
    n8n_service.settings = get_settings()
    google_service.settings = get_settings()
    return GenericMessage(
        message=f"Updated {update.key}.",
        detail={"masked": mask_secret(update.value)},
    )


@router.post("/test/gemini", response_model=ConnectionTestResult)
async def test_gemini() -> ConnectionTestResult:
    result = await gemini_service.test_connection()
    return ConnectionTestResult(
        connected=result.get("connected", False),
        detail=result.get("detail", ""),
        suggestion=result.get("suggestion"),
    )


@router.post("/test/n8n", response_model=ConnectionTestResult)
async def test_n8n() -> ConnectionTestResult:
    result = await n8n_service.test_connection()
    return ConnectionTestResult(
        connected=result.get("connected", False),
        detail=result.get("detail", ""),
        suggestion=result.get("suggestion"),
    )


@router.post("/test/google", response_model=ConnectionTestResult)
async def test_google() -> ConnectionTestResult:
    sheets = await google_service.test_sheets()
    gmail = await google_service.test_gmail()
    if sheets["connected"] and gmail["connected"]:
        return ConnectionTestResult(
            connected=True,
            detail=f"Sheets: {sheets['detail']} | Gmail: {gmail['detail']}",
        )
    if sheets["connected"] or gmail["connected"]:
        return ConnectionTestResult(
            connected=False,
            detail=f"Sheets: {sheets['detail']} | Gmail: {gmail['detail']}",
            suggestion="Both Sheets and Gmail should be reachable. Re-check missing scopes.",
        )
    return ConnectionTestResult(
        connected=False,
        detail=f"Sheets: {sheets['detail']} | Gmail: {gmail['detail']}",
        suggestion=sheets.get("suggestion") or gmail.get("suggestion"),
    )
